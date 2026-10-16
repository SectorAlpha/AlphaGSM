"""Local-only security checks for reusable SteamCMD sessions."""
import importlib
import json
import os
from pathlib import Path
import subprocess

import pytest


def auth_module():
    spec = importlib.util.find_spec('utils.steam_auth')
    assert spec is not None, 'secure SteamCMD profile support is missing'
    return importlib.import_module('utils.steam_auth')


@pytest.fixture
def auth(tmp_path, monkeypatch):
    module = auth_module()
    monkeypatch.setattr(module, '_state_root', lambda: tmp_path / 'state')
    monkeypatch.setattr(module, 'PLATFORM', 'linux')
    return module


def session(auth, name='owned'):
    with auth.locked_profile(name, create=True) as profile:
        (profile / 'runtime/config').mkdir(parents=True, mode=0o700)
        (profile / 'runtime/config/config.vdf').write_text('cached-secret-token')
        (profile / 'runtime/steamcmd.sh').write_text('#!/bin/sh\n')
        (profile / 'runtime/steamcmd.sh').chmod(0o700)
        auth.write_metadata(profile, 'account_name')
    return profile


def test_feature_exists():
    assert auth_module()


@pytest.mark.parametrize('name', ['../escape', '/absolute', '.', '', 'a/b', 'a b', '+quit'])
def test_rejects_unsafe_names_before_creating_state(auth, name):
    with pytest.raises(auth.SteamAuthError, match='profile name'):
        auth.status(name)
    assert not auth._state_root().exists()


def test_profile_and_metadata_are_private_and_status_does_not_reveal_tokens(auth):
    profile = session(auth)
    result = auth.status('owned')
    assert result == {'profile': 'owned', 'local_session': True}
    assert 'cached-secret' not in str(result)
    for directory in (profile.parent, profile, profile / 'runtime'):
        assert directory.stat().st_mode & 0o777 == 0o700
    assert (profile / 'profile.json').stat().st_mode & 0o777 == 0o600
    assert (profile / 'runtime/config/config.vdf').stat().st_mode & 0o777 == 0o600


def test_missing_profile_status_and_download_fail_closed(auth):
    assert auth.status('missing') == {'profile': 'missing', 'local_session': False}
    with pytest.raises(auth.SteamAuthError, match='login'):
        with auth.download_session('missing'):
            pytest.fail('must not use an anonymous fallback')


def test_rejects_profile_and_nested_symlinks(auth, tmp_path):
    profile = session(auth)
    outside = tmp_path / 'outside'
    outside.write_text('private')
    (profile / 'runtime/linked').symlink_to(outside)
    with pytest.raises(auth.SteamAuthError, match='symbolic link'):
        auth.status('owned')
    assert outside.read_text() == 'private'


def test_rejects_unexpected_owner(auth, monkeypatch):
    profile = session(auth)
    actual_uid = os.getuid()
    monkeypatch.setattr(auth.os, 'getuid', lambda: actual_uid + 1)
    with pytest.raises(auth.SteamAuthError, match='owner'):
        auth.status('owned')
    assert profile.exists()


def test_logout_deletes_only_selected_cached_profile(auth):
    profile = session(auth)
    other = session(auth, 'other')
    auth.logout('owned')
    assert not profile.exists()
    assert other.exists()
    assert not auth.status('owned')['local_session']


def test_profile_lock_prevents_concurrent_operations(auth):
    session(auth)
    with auth.locked_profile('owned'):
        with pytest.raises(auth.SteamAuthError, match='in use'):
            auth.logout('owned')


def test_login_inherits_terminal_and_never_passes_a_password(auth, monkeypatch):
    calls = []
    def install(profile):
        (profile / 'runtime/config').mkdir(parents=True)
        executable = profile / 'runtime/steamcmd.sh'
        executable.write_text('#!/bin/sh\n')
        executable.chmod(0o700)
        return executable
    def run(command, **kwargs):
        calls.append((command, kwargs))
        (Path(kwargs['cwd']) / 'config/config.vdf').write_text('private-session')
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(auth, '_install_runtime', install)
    monkeypatch.setattr(auth.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(auth, 'run_steamcmd', run)
    auth.login('owned', 'account_name')
    command, kwargs = calls[0]
    assert command[1:] == ['+login', 'account_name', '+quit']
    assert not {'stdout', 'stderr', 'input'} & kwargs.keys()
    assert kwargs['env']['HOME'].endswith('/owned/home')
    assert kwargs['umask'] == 0o077
    assert auth.status('owned')['local_session']
    assert json.loads((auth._state_root() / 'steam-auth/owned/profile.json').read_text()) == {'username': 'account_name'}


def test_nonlinux_rejected_before_creation(auth, monkeypatch):
    monkeypatch.setattr(auth, 'PLATFORM', 'windows')
    with pytest.raises(auth.SteamAuthError, match='Linux'):
        auth.login('owned', 'account_name')
    assert not auth._state_root().exists()


def test_download_uses_isolated_session_and_suppresses_private_output(auth, monkeypatch, capsys, tmp_path):
    from utils import steamcmd
    profile = session(auth)
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "secret-token\nSuccess! App '123' fully installed.\n")
    monkeypatch.setattr(auth, 'run_steamcmd', run)
    monkeypatch.setattr(steamcmd, 'install_steamcmd', lambda: pytest.fail('must not touch desktop Steam'))
    steamcmd.download(tmp_path / 'files', 123, False, auth_profile='owned')
    command, kwargs = calls[0]
    assert command[0] == str(profile / 'runtime/steamcmd.sh')
    assert command[command.index('+login') + 1] == 'account_name'
    assert 'anonymous' not in command
    assert '+@NoPromptForPassword' in command
    assert kwargs['stdin'] == subprocess.DEVNULL
    assert 'secret-token' not in capsys.readouterr().out


def test_download_failure_does_not_expose_private_output_or_exception(auth, monkeypatch, capsys, tmp_path):
    from utils import steamcmd
    profile = session(auth)
    def run(*_args, **_kwargs):
        (profile / 'runtime/log.txt').write_text('private')
        raise OSError('private-token-from-steam')
    monkeypatch.setattr(auth, 'run_steamcmd', run)
    with pytest.raises(auth.SteamAuthError) as error:
        steamcmd.download(tmp_path / 'files', 123, False, auth_profile='owned')
    assert 'private-token' not in str(error.value)
    assert error.value.__cause__ is None
    assert 'private-token' not in capsys.readouterr().out
    assert (profile / 'runtime/log.txt').stat().st_mode & 0o777 == 0o600


def test_root_and_profile_links_are_rejected(auth, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir(mode=0o700)
    auth._state_root().symlink_to(outside, target_is_directory=True)
    with pytest.raises(auth.SteamAuthError, match='symbolic link'):
        with auth.locked_profile('owned', create=True):
            pytest.fail('must reject linked state root')
    assert not list(outside.iterdir())


def test_rejects_shared_profile_directory(auth):
    profile = session(auth)
    profile.chmod(0o755)
    with pytest.raises(auth.SteamAuthError, match='owner-only'):
        auth.status('owned')


def test_missing_cache_and_executable_cannot_be_download_sessions(auth):
    profile = session(auth)
    (profile / 'runtime/config/config.vdf').unlink()
    with pytest.raises(auth.SteamAuthError, match='session missing'):
        with auth.download_session('owned'):
            pytest.fail('missing session must fail')
    assert not auth.status('owned')['local_session']


def test_login_requires_a_terminal_without_creating_state(auth, monkeypatch):
    monkeypatch.setattr(auth.sys.stdin, 'isatty', lambda: False)
    with pytest.raises(auth.SteamAuthError, match='interactive terminal'):
        auth.login('owned', 'account_name')
    assert not auth._state_root().exists()


@pytest.mark.parametrize('username', ['anonymous', '+quit', 'account password', 'a\npassword'])
def test_login_rejects_commandlike_account_names(auth, monkeypatch, username):
    monkeypatch.setattr(auth.sys.stdin, 'isatty', lambda: True)
    with pytest.raises(auth.SteamAuthError, match='username'):
        auth.login('owned', username)
    assert not auth._state_root().exists()


def test_login_failure_invalidates_metadata_and_restores_private_modes(auth, monkeypatch):
    profile = session(auth)
    monkeypatch.setattr(auth.sys.stdin, 'isatty', lambda: True)
    monkeypatch.setattr(auth, '_install_runtime', lambda _profile: profile / 'runtime/steamcmd.sh')
    def failed(*_args, **_kwargs):
        log = profile / 'runtime/log.txt'
        log.write_text('secret')
        log.chmod(0o666)
        raise OSError('raw-secret-token')
    monkeypatch.setattr(auth, 'run_steamcmd', failed)
    with pytest.raises(auth.SteamAuthError) as error:
        auth.login('owned', 'account_name')
    assert 'raw-secret' not in str(error.value)
    assert not (profile / 'profile.json').exists()
    assert (profile / 'runtime/log.txt').stat().st_mode & 0o777 == 0o600


def test_installer_uses_official_bootstrap_and_rejects_archive_traversal(auth, monkeypatch, tmp_path):
    import io
    import tarfile
    downloads = []
    def archive_download(path, args):
        downloads.append(args)
        with tarfile.open(Path(path) / args[1], 'w:gz') as archive:
            member = tarfile.TarInfo('../escaped')
            member.size = 1
            archive.addfile(member, io.BytesIO(b'x'))
    monkeypatch.setattr(auth, 'url_download', archive_download)
    with auth.locked_profile('owned', create=True) as profile:
        with pytest.raises(auth.SteamAuthError, match='archive member'):
            auth._install_runtime(profile)
        assert not (profile / 'escaped').exists()
    assert downloads[0][0].startswith('https://steamcdn-a.akamaihd.net/')


def test_download_process_nonzero_never_exposes_token(auth, monkeypatch, tmp_path, capsys):
    from utils import steamcmd
    session(auth)
    monkeypatch.setattr(auth, 'run_steamcmd', lambda command, **kwargs: subprocess.CompletedProcess(
        command, 1, 'cached-secret-token'))
    with pytest.raises(auth.SteamAuthError) as error:
        steamcmd.download(tmp_path / 'files', 123, True, auth_profile='owned')
    assert 'cached-secret' not in str(error.value)
    assert 'cached-secret' not in capsys.readouterr().out


def test_missing_explicit_profile_never_installs_or_runs_steamcmd(auth, monkeypatch, tmp_path):
    from utils import steamcmd
    monkeypatch.setattr(steamcmd, 'install_steamcmd', lambda: pytest.fail('no legacy install'))
    monkeypatch.setattr(auth, 'run_steamcmd', lambda *args, **kwargs: pytest.fail('no anonymous process'))
    with pytest.raises(auth.SteamAuthError, match='login'):
        steamcmd.download(tmp_path / 'files', 123, True, auth_profile='missing')


def test_profile_environment_excludes_desktop_steam_variables(auth, monkeypatch):
    profile = session(auth)
    monkeypatch.setenv('STEAM_COMPAT_CLIENT_INSTALL_PATH', '/desktop/Steam')
    monkeypatch.setenv('STEAMROOT', '/desktop/Steam')
    with auth.download_session('owned') as (_exe, _username, env, _lock_fd):
        assert 'STEAMROOT' not in env
        assert 'STEAM_COMPAT_CLIENT_INSTALL_PATH' not in env
        for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'):
            assert Path(env[key]).is_relative_to(profile)


def test_session_cleanup_rejects_hard_links_without_chmodding_target(auth, tmp_path):
    profile = session(auth)
    outside = tmp_path / 'outside'
    outside.write_text('private')
    outside.chmod(0o644)
    os.link(outside, profile / 'runtime/hardlink')
    with pytest.raises(auth.SteamAuthError, match='hard-linked'):
        auth.status('owned')
    assert outside.stat().st_mode & 0o777 == 0o644


def test_bootstrap_failure_is_reported_without_raw_installer_details(auth, monkeypatch):
    from downloader import DownloaderError
    monkeypatch.setattr(auth.sys.stdin, 'isatty', lambda: True)
    def fail(_profile):
        raise DownloaderError('raw bootstrap detail')
    monkeypatch.setattr(auth, '_install_runtime', fail)
    with pytest.raises(auth.SteamAuthError, match='login failed') as error:
        auth.login('owned', 'account_name')
    assert 'raw bootstrap' not in str(error.value)


def test_profile_download_rejects_branch_password_before_it_can_reach_argv(auth, monkeypatch, tmp_path):
    from utils import steamcmd
    session(auth)
    monkeypatch.setattr(auth, 'run_steamcmd', lambda *args, **kwargs: pytest.fail('password must not reach argv'))
    with pytest.raises(auth.SteamAuthError, match='Branch passwords') as error:
        steamcmd.download(tmp_path / 'files', 123, False, auth_profile='owned',
                          beta_branch='private', beta_password='secret-branch-password')
    assert 'secret-branch-password' not in str(error.value)


def test_lock_symlink_is_rejected_with_safe_profile_error(auth, tmp_path):
    profile = session(auth)
    lock = profile.parent / '.owned.lock'
    lock.unlink()
    outside = tmp_path / 'outside'
    outside.write_text('private')
    lock.symlink_to(outside)
    with pytest.raises(auth.SteamAuthError, match='lock'):
        auth.status('owned')
    assert outside.read_text() == 'private'


@pytest.mark.parametrize('mode', [0o777, 0o775])
def test_rejects_state_root_below_renameable_ancestor(auth, monkeypatch, tmp_path, mode):
    parent = tmp_path / 'shared'
    parent.mkdir(mode=mode)
    parent.chmod(mode)
    monkeypatch.setattr(auth, '_state_root', lambda: parent / 'private/state')
    with pytest.raises(auth.SteamAuthError, match='ancestor'):
        with auth.locked_profile('owned', create=True):
            pytest.fail('another user can rename the private state root ancestor')
    assert not (parent / 'private').exists()


def test_sticky_ancestor_requires_a_trusted_owner(auth, monkeypatch, tmp_path):
    from types import SimpleNamespace
    parent = tmp_path / 'sticky'
    parent.mkdir(mode=0o700)
    monkeypatch.setattr(auth, '_state_root', lambda: parent / 'state')
    original = Path.lstat
    def lstat(path):
        actual = original(path)
        if path == parent:
            return SimpleNamespace(st_mode=0o41777, st_uid=os.getuid() + 1)
        return actual
    monkeypatch.setattr(Path, 'lstat', lstat)
    with pytest.raises(auth.SteamAuthError, match='ancestor.*owner'):
        with auth.locked_profile('owned', create=True):
            pytest.fail('an untrusted sticky directory owner can rename all entries')


def _wait_until(predicate, timeout=5):
    import time
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError('offline child did not reach expected state')


def _live_process(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
    except FileNotFoundError:
        return False


def _fake_download_manager(auth, tmp_path, operation="download"):
    """Start a manager and fake SteamCMD tree; no network, credentials or Steam."""
    import sys
    profile = session(auth)
    ready = tmp_path / 'ready'
    descendant = tmp_path / 'descendant'
    release = tmp_path / 'release'
    script = profile / 'runtime/steamcmd.sh'
    script.write_text(f'''#!{sys.executable}
import os
from pathlib import Path
import subprocess
import sys
import time
child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
Path({str(descendant)!r}).write_text(str(child.pid))
Path({str(ready)!r}).write_text(str(os.getpid()))
while not Path({str(release)!r}).exists():
    time.sleep(.02)
child.terminate()
child.wait()
print("Success! App '123' fully installed.")
''')
    script.chmod(0o700)
    invoke = (f"steamcmd.download({str(tmp_path / 'files')!r}, 123, False, auth_profile='owned')"
              if operation == 'download' else
              "steam_auth.sys.stdin.isatty = lambda: True; steam_auth.login('owned', 'account_name')")
    source = f'''from pathlib import Path
from utils import steam_auth, steamcmd
steam_auth._state_root = lambda: Path({str(auth._state_root())!r})
{invoke}
'''
    env = dict(os.environ)
    src_root = str(Path(__file__).resolve().parents[3] / 'src')
    env['PYTHONPATH'] = os.pathsep.join(filter(None, (src_root, env.get('PYTHONPATH'))))
    manager = subprocess.Popen([sys.executable, '-c', source], env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        _wait_until(ready.exists)
    except BaseException:
        manager.kill()
        manager.wait()
        raise
    return manager, int(ready.read_text()), int(descendant.read_text()), release


def _cleanup_fake_manager(manager, *pids):
    import signal
    if manager.poll() is None:
        manager.kill()
    manager.wait(timeout=5)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.parametrize("operation", ["login", "download"])
def test_live_child_retains_profile_lock_after_manager_is_killed(auth, tmp_path, operation):
    manager, child, descendant, release = _fake_download_manager(auth, tmp_path, operation)
    try:
        manager.kill()
        manager.wait(timeout=5)
        assert _live_process(child)
        with pytest.raises(auth.SteamAuthError, match='in use'):
            auth.logout('owned')
        release.touch()
        _wait_until(lambda: not _live_process(child))
        auth.logout('owned')
    finally:
        _cleanup_fake_manager(manager, child, descendant)


@pytest.mark.parametrize("operation", ["login", "download"])
def test_sigterm_stops_child_tree_and_releases_profile_lock(auth, tmp_path, operation):
    manager, child, descendant, _release = _fake_download_manager(auth, tmp_path, operation)
    try:
        manager.terminate()
        manager.wait(timeout=5)
        _wait_until(lambda: not _live_process(child) and not _live_process(descendant), timeout=2)
        auth.logout('owned')
    finally:
        _cleanup_fake_manager(manager, child, descendant)
