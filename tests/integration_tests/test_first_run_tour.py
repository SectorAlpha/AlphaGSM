"""Real CLI tour checks with isolated config; no game downloads or launches."""

import errno
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import time

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def cli_home(tmp_path):
    home = tmp_path / 'operator'
    config = tmp_path / 'alphagsm.conf'
    config.write_text('[core]\nalphagsm_path = %s\nuserconf = %s\n[server]\ndatapath = %s\n' %
                      (home, home, home / 'conf'))
    env = dict(os.environ, ALPHAGSM_CONFIG_LOCATION=str(config),
               ALPHAGSM_USERCONFIG_LOCATION=str(tmp_path / 'missing-user.conf'))
    return home, env


def run_cli(env, *args):
    return subprocess.run([sys.executable, str(REPO / 'alphagsm'), *args], env=env,
                          cwd=REPO, capture_output=True, text=True, check=False, timeout=15)


def run_terminal(env, args, answers):
    pty = pytest.importorskip('pty', reason='Interactive terminal coverage requires POSIX PTY support')
    master, slave = pty.openpty()
    process = subprocess.Popen([sys.executable, str(REPO / 'alphagsm'), *args], env=env,
                               cwd=REPO, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = bytearray()
    try:
        os.write(master, answers.encode())
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master, 8192)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
            elif process.poll() is not None:
                break
        return process.wait(timeout=2), output.decode(errors='replace')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        os.close(master)


def test_piped_invocation_keeps_help_behavior_without_state(cli_home):
    home, env = cli_home
    result = run_cli(env)
    assert result.returncode == 2
    assert 'Start the optional setup tour' not in result.stdout
    assert not home.exists()


def test_explicit_skip_is_noninteractive_and_replay_is_documented(cli_home):
    home, env = cli_home
    result = run_cli(env, '--skip-welcome')
    assert result.returncode == 0, result.stderr
    assert '--welcome' in result.stdout
    assert (home / 'welcome-v1.done').read_text() == 'skipped\n'
    assert not (home / 'agent').exists() and not (home / 'conf').exists()


def test_real_terminal_first_run_skip_and_explicit_replay(cli_home):
    home, env = cli_home
    code, output = run_terminal(env, [], '\n')
    assert code == 0, output
    assert 'Start the optional setup tour' in output
    assert (home / 'welcome-v1.done').read_text() == 'skipped\n'
    code, output = run_terminal(env, [], '')
    assert code == 2 and 'Start the optional setup tour' not in output
    code, output = run_terminal(env, ['--welcome'], '\n')
    assert code == 0 and 'Welcome to AlphaGSM' in output
    assert (home / 'welcome-v1.done').read_text() == 'skipped\n'
    assert not (home / 'agent').exists()


def test_real_tour_creates_only_approved_local_record_and_skips_downloads(cli_home):
    home, env = cli_home
    code, output = run_terminal(env, ['--welcome'], '1\nminecraft\nworld\ny\nn\n\n')
    assert code == 0, output
    record = json.loads((home / 'conf/world.json').read_text())
    assert record['module'] == 'minecraft.vanilla'
    assert 'Run setup now?' in output
    assert not (home / 'agent').exists()
    assert not (home / 'servers').exists()


def test_real_tour_preserves_existing_server_bytes(cli_home):
    home, env = cli_home
    (home / 'conf').mkdir(parents=True)
    record = home / 'conf/world.json'
    record.write_text('{"module":"minecraft.paper","world":"keep-me"}')
    before = record.read_bytes()
    code, output = run_terminal(env, ['--welcome'], '1\ntf2\nworld\n\n')
    assert code == 0, output
    assert 'already exists' in output and record.read_bytes() == before
    assert not (home / 'agent').exists()


def test_explicit_tour_requires_a_terminal_but_help_and_version_do_not(cli_home):
    home, env = cli_home
    result = run_cli(env, '--welcome')
    assert result.returncode == 2 and 'interactive input and output' in result.stderr
    for args in [('--welcome', '--help'), ('--version',), ('--help',)]:
        result = run_cli(env, *args)
        assert result.returncode == 0, result.stderr
    assert not home.exists()


def test_server_named_welcome_still_uses_normal_dispatch(cli_home):
    home, env = cli_home
    result = run_cli(env, 'welcome', 'create', 'minecraft.vanilla')
    assert result.returncode == 0, result.stderr
    assert (home / 'conf/welcome.json').is_file()
    assert not (home / 'welcome-v1.done').exists()


@pytest.mark.parametrize('tag', ['all', 'ALL', '1', '02', 'agent', 'self-update', 'start'])
def test_real_tour_rejects_cli_selectors_and_reserved_names(cli_home, tag):
    home, env = cli_home
    (home / 'conf').mkdir(parents=True)
    record = home / 'conf/world.json'
    record.write_text('{"module":"minecraft.vanilla","port":25565,"keep":"existing world"}')
    before = record.read_bytes()
    code, output = run_terminal(env, ['--welcome'], '1\ntf2\n' + tag + '\ny\nn\n\n')
    assert code == 0, output
    assert 'reserved' in output, output
    assert 'Create a local server record:' not in output
    assert record.read_bytes() == before
    assert sorted(path.name for path in (home / 'conf').glob('*.json')) == ['world.json']
    assert not (home / 'agent').exists()
