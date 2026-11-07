"""CI config and smoke runtime regressions without downloads or server launches."""

import configparser
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('shared_work_dir', [False, True])
@pytest.mark.parametrize('custom_steamcmd', [False, True])
def test_lifecycle_writes_one_steamcmd_section_and_keeps_override(tmp_path, monkeypatch,
                                                                shared_work_dir, custom_steamcmd):
    from tests.integration_tests import conftest as helpers
    monkeypatch.setitem(sys.modules, 'conftest', helpers)
    spec = importlib.util.spec_from_file_location('_asrd_ci_config', ROOT / 'tests/integration_tests/test_asrdserver.py')
    integration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integration)
    if shared_work_dir:
        monkeypatch.setenv('ALPHAGSM_WORK_DIR', str(tmp_path / 'shared'))
    else:
        monkeypatch.delenv('ALPHAGSM_WORK_DIR', raising=False)
    override = str(tmp_path / 'operator 100% steamcmd')
    if custom_steamcmd:
        monkeypatch.setenv('ALPHAGSM_ASRDSERVER_STEAMCMD_PATH', override)
    else:
        monkeypatch.delenv('ALPHAGSM_ASRDSERVER_STEAMCMD_PATH', raising=False)
    for name in ('require_integration_opt_in', 'require_steamcmd_opt_in', 'require_command_for_runtime'):
        monkeypatch.setattr(integration, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(integration, 'pick_free_tcp_port_group', lambda _count: 27015)

    class BeforeCreate(Exception):
        pass

    def inspect_config(env, name, action, *args, **kwargs):
        del name, args, kwargs
        assert action == 'create'
        path = Path(env['ALPHAGSM_CONFIG_LOCATION'])
        parser = configparser.ConfigParser(interpolation=None)
        parser.read_string(path.read_text())
        assert parser.sections().count('downloader.steamcmd') == 1
        expected = override if custom_steamcmd else str(tmp_path / 'steamcmd')
        assert parser['downloader.steamcmd']['steamcmd_path'] == expected
        assert parser['runtime']['backend'] == 'docker'
        raise BeforeCreate

    monkeypatch.setattr(integration, 'run_and_assert_ok', inspect_config)
    with pytest.raises(BeforeCreate):
        integration.test_asrdserver_lifecycle(tmp_path, runtime_backend='docker')


@pytest.mark.parametrize('backend', ['docker', 'auto', 'process', None])
@pytest.mark.parametrize('fail_start', [False, True])
def test_smoke_runs_cli_baseline_with_only_selected_runtime_prerequisites(tmp_path, backend, fail_start):
    """Replay the actual runner with fake commands; no Wine/Docker or sockets are used."""
    calls = tmp_path / 'commands.jsonl'
    required = tmp_path / 'requirements.txt'
    snapshot = tmp_path / 'smoke-config.ini'
    bootstrap = tmp_path / 'bash-env'
    bootstrap.write_text('''command() {
  if [[ "$1" == -v ]]; then
    printf '%s\\n' "$2" >> "$REQUIRED"
    case "$2" in
      wine|screen) [[ "${ALPHAGSM_TEST_RUNTIME_BACKEND:-}" == process ]]; return ;;
      docker) [[ "${ALPHAGSM_TEST_RUNTIME_BACKEND:-}" != process ]]; return ;;
    esac
  fi
  builtin command "$@"
}
''')
    fake_python = tmp_path / 'python-fixture'
    fake_python.write_text(f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
args = sys.argv[1:]
if args and args[0].endswith('/alphagsm'):
    pathlib.Path(os.environ['SNAPSHOT']).write_text(pathlib.Path(os.environ['ALPHAGSM_CONFIG_LOCATION']).read_text())
    with open(os.environ['CALLS'], 'a') as output:
        output.write(json.dumps(args[1:]) + '\\n')
    if args[2:] == ['start'] and os.environ.get('ASRD_FAIL_START') == '1':
        raise SystemExit(42)
    if args[2:] == ['info', '--json']:
        print(json.dumps({'protocol': 'a2s', 'port': 27015, 'map': 'lobby'}))
    elif args[2:] == ['query']:
        print('Server is responding')
elif args and args[0].endswith('/select_test_port.py'):
    print('27015')
elif args[:1] == ['-c']:
    print('private-fixture-rcon')
elif args[:1] == ['-']:
    sys.stdin.read()
    with open(os.environ['CALLS'], 'a') as output:
        output.write(json.dumps(['shutdown-probe' if len(args) > 1 else 'readiness-probe']) + '\\n')
else:
    raise SystemExit('Unexpected smoke Python invocation')
''')
    fake_python.chmod(0o755)
    env = dict(os.environ, BASH_ENV=str(bootstrap), PYTHON_BIN=str(fake_python),
               REQUIRED=str(required), CALLS=str(calls), SNAPSHOT=str(snapshot), SERVER_NAME='itasrdserver',
               ALPHAGSM_TEST_RUNTIME_BACKEND=backend or 'auto', ALPHAGSM_WORK_DIR=str(tmp_path / 'work'),
               ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON='branch-local-wine:ci-regression',
               ASRD_FAIL_START='1' if fail_start else '0')
    if backend is None:
        env.pop('ALPHAGSM_TEST_RUNTIME_BACKEND')
    for key in list(env):
        if key.startswith('ASRD_WORKSHOP_'):
            env.pop(key)
    result = subprocess.run(['bash', str(ROOT / 'tests/smoke_tests/run_asrdserver.sh')],
                            env=env, capture_output=True, text=True, check=False, timeout=15)
    assert result.returncode == (42 if fail_start else 0), result.stderr or result.stdout
    prerequisites = required.read_text().splitlines()
    docker = backend != 'process'
    assert ('docker' in prerequisites) == docker
    assert ('wine' in prerequisites) == (not docker)
    assert ('screen' in prerequisites) == (not docker)
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(snapshot.read_text())
    assert parser['runtime']['backend'] == ('docker' if docker else 'process')
    if docker:
        assert parser['docker']['image_wine_proton'] == 'branch-local-wine:ci-regression'
    commands = [json.loads(line) for line in calls.read_text().splitlines()]
    actions = [command[1] if len(command) > 1 else command[0] for command in commands]
    assert actions.index('create') < actions.index('setup') < actions.index('start')
    if fail_start:
        assert actions.index('start') < actions.index('stop')
        assert 'query' not in actions and 'shutdown-probe' not in actions
        return
    assert actions.index('start') < actions.index('info') < actions.index('query') < actions.index('stop')
    assert commands.count(['itasrdserver', 'info', '--json']) >= 2
    assert actions.index('stop') < actions.index('shutdown-probe')


def test_failed_start_still_attempts_stop_and_preserves_original_error(tmp_path, monkeypatch):
    """A container can fail after creation, so start itself needs the cleanup guard."""
    from types import SimpleNamespace
    from tests.integration_tests import conftest as helpers
    monkeypatch.setitem(sys.modules, 'conftest', helpers)
    spec = importlib.util.spec_from_file_location('_asrd_failed_start', ROOT / 'tests/integration_tests/test_asrdserver.py')
    integration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(integration)
    for name in ('require_integration_opt_in', 'require_steamcmd_opt_in', 'require_command_for_runtime'):
        monkeypatch.setattr(integration, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(integration, 'pick_free_tcp_port_group', lambda _count: 27015)
    monkeypatch.setattr(integration, 'resolve_wine_proton_runtime_image', lambda: 'fixture-image')
    failure = RuntimeError('native console failed during start')
    result = SimpleNamespace(returncode=0, stdout='', stderr='')
    stopped = []

    def run(_env, name, action, *_args, **_kwargs):
        if action == 'setup':
            install = tmp_path / 'server'
            install.mkdir()
            (install / 'srcds_console.exe').write_bytes(b'fixture engine')
            config = tmp_path / 'home/conf'
            config.mkdir()
            (config / f'{name}.json').write_text(json.dumps({'wineprefix': str(install / '.wine')}))
        if action == 'start':
            raise failure
        return result

    monkeypatch.setattr(integration, 'run_and_assert_ok', run)
    monkeypatch.setattr(integration, 'capture_alphagsm_stop',
                        lambda *args: stopped.append(args[2]) or result)
    with pytest.raises(RuntimeError) as raised:
        integration.test_asrdserver_lifecycle(tmp_path, runtime_backend='docker')
    assert raised.value is failure and stopped == [failure]
