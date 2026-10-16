"""Private, isolated Linux SteamCMD sessions without saved account passwords."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import subprocess as sp
import sys
import tarfile
import threading

from downloader import DownloaderError
from downloadermodules.url import download as url_download
from utils.platform_info import PLATFORM
from utils.settings import settings


class SteamAuthError(RuntimeError):
    """A profile cannot safely be used for a SteamCMD operation."""


def _state_root():
    """Return the configured AlphaGSM state directory without following links."""
    value = settings.user.getsection('core').get('alphagsm_path', '~/.alphagsm')
    return Path(os.path.abspath(os.path.expanduser(value)))


def _validate_name(name):
    """Accept only unambiguous local profile identifiers."""
    if not isinstance(name, str) or re.fullmatch(r'[A-Za-z0-9_-]+', name) is None:
        raise SteamAuthError('Invalid SteamCMD profile name; use letters, numbers, _ or -')


def _check_path(path, private=False):
    """Reject links, other owners, special files and shared private paths."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise SteamAuthError('Unsafe SteamCMD profile: symbolic link')
    if info.st_uid != os.getuid():
        raise SteamAuthError('Unsafe SteamCMD profile: unexpected owner')
    if not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
        raise SteamAuthError('Unsafe SteamCMD profile: unexpected file type')
    if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
        raise SteamAuthError('Unsafe SteamCMD profile: hard-linked file')
    if private and info.st_mode & 0o077:
        raise SteamAuthError('Unsafe SteamCMD profile: permissions must be owner-only')
    return info


def _check_ancestor(path):
    """Require ancestors whose owners and rename permissions are trusted."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise SteamAuthError('Unsafe SteamCMD profile: symbolic link in ancestor path')
    if not stat.S_ISDIR(info.st_mode):
        raise SteamAuthError('Unsafe SteamCMD profile: ancestor is not a directory')
    # A sticky directory owner can rename every entry, regardless of child owner.
    if info.st_uid not in (0, os.getuid()):
        raise SteamAuthError('Unsafe SteamCMD profile: unexpected ancestor owner')
    if info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX:
        raise SteamAuthError('Unsafe SteamCMD profile: ancestor permits renaming by other users')


def _directory(path, create=False, private=True):
    """Validate the whole trusted ancestor chain before using or creating state."""
    for parent in reversed(path.parents):
        try:
            _check_ancestor(parent)
        except FileNotFoundError:
            if not create:
                raise
            parent.mkdir(mode=0o700)
            _check_ancestor(parent)
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    info = _check_path(path, private=private)
    if not stat.S_ISDIR(info.st_mode):
        raise SteamAuthError('Unsafe SteamCMD profile: expected directory')


def _secure_tree(profile):
    """Validate all cached files, then restore owner-only permissions."""
    paths = [profile]
    for directory, directories, files in os.walk(profile, followlinks=False):
        paths.extend(Path(directory) / item for item in directories + files)
    checked = [(path, _check_path(path)) for path in paths]
    for path, info in checked:
        mode = 0o700 if stat.S_ISDIR(info.st_mode) or info.st_mode & 0o100 else 0o600
        path.chmod(mode)


@contextmanager
def locked_profile(name, create=False, pass_lock=False):
    """Hold the lock; pass_lock also yields its FD for child inheritance."""
    _validate_name(name)
    if PLATFORM != 'linux':
        raise SteamAuthError('SteamCMD auth profiles require the Linux host installer')
    # fcntl is unavailable on Windows; reject before importing it.
    import fcntl  # pylint: disable=import-outside-toplevel
    root = _state_root()
    try:
        _directory(root, create=create, private=False)
        if root.stat().st_mode & 0o022:
            raise SteamAuthError('Unsafe SteamCMD state directory: writable by other users')
        auth_root = root / 'steam-auth'
        _directory(auth_root, create=create)
    except FileNotFoundError:
        raise SteamAuthError('SteamCMD profile missing; run alphagsm steam-auth login PROFILE USERNAME') from None
    lock_path = auth_root / ('.' + name + '.lock')
    try:
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise SteamAuthError('Cannot safely open the SteamCMD profile lock') from None
    try:
        _check_path(lock_path, private=True)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SteamAuthError('SteamCMD profile is in use; retry after its operation finishes') from None
        profile = auth_root / name
        try:
            _directory(profile, create=create)
        except FileNotFoundError:
            raise SteamAuthError('SteamCMD profile missing; run alphagsm steam-auth login PROFILE USERNAME') from None
        _secure_tree(profile)
        try:
            yield (profile, descriptor) if pass_lock else profile
        finally:
            if profile.exists():
                _secure_tree(profile)
    finally:
        os.close(descriptor)


def write_metadata(profile, username):
    """Store only the account identifier after an interactive login."""
    target = profile / 'profile.json'
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
        json.dump({'username': username}, output)


def _session_username(profile):
    """Require local session material; it is never proof of remote entitlement."""
    try:
        username = json.loads((profile / 'profile.json').read_text(encoding='utf-8'))['username']
        caches = (profile / 'home/Steam/config/config.vdf',
                  profile / 'runtime/config/config.vdf')
        if not any(cache.is_file() and cache.stat().st_size for cache in caches):
            raise ValueError
        if not isinstance(username, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', username):
            raise ValueError
        if not (profile / 'runtime/steamcmd.sh').is_file():
            raise ValueError
        return username
    except (OSError, ValueError, KeyError, TypeError):
        raise SteamAuthError('SteamCMD local session missing; run alphagsm steam-auth login PROFILE USERNAME') from None


def _environment(profile):
    """Keep Steam state and XDG files separate from the desktop client."""
    env = {key: value for key, value in os.environ.items() if not key.startswith('STEAM')}
    home = profile / 'home'
    _directory(home, create=True)
    env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / '.config'),
               XDG_DATA_HOME=str(home / '.local/share'), XDG_CACHE_HOME=str(home / '.cache'))
    return env


def _install_runtime(profile):
    """Install Valve's Linux bootstrap into this profile, rejecting archive links."""
    runtime = profile / 'runtime'
    _directory(runtime, create=True)
    executable = runtime / 'steamcmd.sh'
    if not executable.exists():
        from utils.steamcmd import STEAMCMD_URL  # pylint: disable=import-outside-toplevel
        archive = runtime / 'steamcmd_linux.tar.gz'
        url_download(str(runtime), (STEAMCMD_URL, archive.name))
        with tarfile.open(archive, 'r:gz') as source:
            for member in source.getmembers():
                path = Path(member.name)
                if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                    raise SteamAuthError('Unsafe SteamCMD runtime archive member')
            source.extractall(runtime)  # pylint: disable=unspecified-encoding
        archive.unlink()
    _secure_tree(profile)
    return executable


def _terminate_process_tree(process):
    """Stop the isolated process group and reap its direct SteamCMD child."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except sp.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()
    # The launcher may exit before a descendant that ignores SIGTERM.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def run_steamcmd(command, *, lock_fd, **kwargs):
    """Retain the lock in the child; terminate and reap its group on interruption."""
    if threading.current_thread() is not threading.main_thread():
        raise SteamAuthError('SteamCMD session operations must run on the main thread')
    kwargs.pop('check', None)
    signals = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
    previous = {number: signal.getsignal(number) for number in signals}

    def interrupted(number, _frame):
        if number == signal.SIGINT:
            raise KeyboardInterrupt
        raise SteamAuthError('SteamCMD session operation interrupted')

    try:
        with sp.Popen(command, pass_fds=(lock_fd,), start_new_session=True, **kwargs) as process:
            try:
                for number in signals:
                    signal.signal(number, interrupted)
                output, errors = process.communicate()
                return sp.CompletedProcess(command, process.returncode, output, errors)
            finally:
                # Do not interrupt termination/reaping with a second ordinary signal.
                for number in signals:
                    signal.signal(number, signal.SIG_IGN)
                _terminate_process_tree(process)
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def login(name, username):
    """Let SteamCMD read password and Guard directly from the operator terminal."""
    _validate_name(name)
    if PLATFORM != 'linux':
        raise SteamAuthError('SteamCMD auth profiles require the Linux host installer')
    if not re.fullmatch(r'[A-Za-z0-9_-]+', username) or username.lower() == 'anonymous':
        raise SteamAuthError('Invalid Steam account username')
    if not sys.stdin.isatty():
        raise SteamAuthError('SteamCMD login requires an interactive terminal for password and Steam Guard')
    with locked_profile(name, create=True, pass_lock=True) as (profile, lock_fd):
        # Invalidate prior metadata before attempting a new account login.
        (profile / 'profile.json').unlink(missing_ok=True)
        try:
            executable = _install_runtime(profile)
            result = run_steamcmd([str(executable), '+login', username, '+quit'],
                            cwd=str(executable.parent), env=_environment(profile),
                            umask=0o077, check=False, lock_fd=lock_fd)
        except (OSError, sp.SubprocessError, tarfile.TarError, DownloaderError):
            raise SteamAuthError('SteamCMD login failed; retry interactively') from None
        if result.returncode != 0:
            raise SteamAuthError('SteamCMD login failed; retry interactively')
        write_metadata(profile, username)
        _session_username(profile)


def status(name):
    """Report local cached state only, without reading out credentials."""
    _validate_name(name)
    try:
        with locked_profile(name) as profile:
            try:
                _session_username(profile)
                present = True
            except SteamAuthError:
                present = False
    except SteamAuthError as error:
        if 'profile missing;' not in str(error):
            raise
        present = False
    return {'profile': name, 'local_session': present}


def logout(name):
    """Delete this local cached profile; this does not revoke Valve sessions."""
    with locked_profile(name) as profile:
        shutil.rmtree(profile)


@contextmanager
def download_session(name):
    """Yield executable, username, environment and inheritable lock descriptor."""
    with locked_profile(name, pass_lock=True) as (profile, lock_fd):
        username = _session_username(profile)
        yield profile / 'runtime/steamcmd.sh', username, _environment(profile), lock_fd
