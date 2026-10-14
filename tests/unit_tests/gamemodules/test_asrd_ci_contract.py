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
def test_smoke_runs_cli_baseline_with_only_selected_runtime_prerequisites(tmp_path, backend):
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
               ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON='branch-local-wine:ci-regression')
    if backend is None:
        env.pop('ALPHAGSM_TEST_RUNTIME_BACKEND')
    for key in list(env):
        if key.startswith('ASRD_WORKSHOP_'):
            env.pop(key)
    result = subprocess.run(['bash', str(ROOT / 'tests/smoke_tests/run_asrdserver.sh')],
                            env=env, capture_output=True, text=True, check=False, timeout=15)
    assert result.returncode == 0, result.stderr or result.stdout
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
    assert actions.index('start') < actions.index('info') < actions.index('query') < actions.index('stop')
    assert commands.count(['itasrdserver', 'info', '--json']) >= 2
    assert actions.index('stop') < actions.index('shutdown-probe')
