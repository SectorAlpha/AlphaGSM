"""Source smoke wrappers keep redirected CLI evidence machine readable."""

import json
import os
import subprocess
import sys

import pytest

from tests.helpers import REPO_ROOT


@pytest.mark.parametrize('runner', [
    'run_bb2server.sh', 'run_doiserver.sh', 'run_insserver.sh',
    'run_nmrihserver.sh', 'run_tf2.sh',
])
def test_source_smoke_wrapper_preserves_json_stdout_and_command_status(tmp_path, runner):
    script = (REPO_ROOT / 'tests/smoke_tests' / runner).read_text()
    wrapper = 'run_alphagsm() {' + script.split('run_alphagsm() {', 1)[1].split('\n}', 1)[0] + '\n}'
    fake_cli = tmp_path / 'fake_alphagsm.py'
    fake_cli.write_text(
        'import json, os, sys\n'
        'print(json.dumps({"protocol": "a2s", "map": "custom", "args": sys.argv[1:], '
        '"config": os.environ["ALPHAGSM_CONFIG_LOCATION"]}))\n'
        'sys.exit(int(os.environ["COMMAND_STATUS"]))\n'
    )
    for status in (0, 23):
        result = subprocess.run(
            ['bash', '-c', wrapper + '\nrun_alphagsm fixture info --json'],
            env=dict(os.environ, CONFIG_PATH=str(tmp_path / 'config'), REPO_ROOT=str(REPO_ROOT),
                     PYTHON_BIN=sys.executable, ALPHAGSM_SCRIPT=str(fake_cli), COMMAND_STATUS=str(status)),
            capture_output=True, text=True, check=False,
        )
        assert result.returncode == status
        assert json.loads(result.stdout) == {
            'protocol': 'a2s', 'map': 'custom', 'args': ['fixture', 'info', '--json'],
            'config': str(tmp_path / 'config'),
        }
        assert '=== alphagsm fixture info --json ===' in result.stderr


@pytest.mark.parametrize('ready_only', [False, True])
@pytest.mark.parametrize('scenario', ['delayed', 'stale', 'incomplete', 'stock', 'pending'])
@pytest.mark.parametrize('deadline', [3, 30])
def test_tf2_smoke_waits_for_its_buffered_native_response(tmp_path, ready_only, scenario, deadline):
    script = (REPO_ROOT / 'tests/smoke_tests/run_tf2.sh').read_text()
    probe = 'capture_native_workshop_probe() {' + script.split(
        'capture_native_workshop_probe() {', 1)[1].split('\n}', 1)[0] + '\n}'
    fake_console = r'''
SEND_COUNT=0
LOG_READS=0
unset SECONDS
SECONDS=0
sleep() { SECONDS=$((SECONDS + 1)); }
run_alphagsm() {
  if [[ "$2" == send ]]; then
    SEND_COUNT=$((SEND_COUNT + 1))
    local payload="${3#echo BEGIN-}"
    CURRENT_TOKEN="${payload%%;*}"
    return 0
  fi
  LOG_READS=$((LOG_READS + 1))
  local token="$CURRENT_TOKEN" map="workshop/cp_orange_x3.ugc454299390" state=ready
  if [[ "$SCENARIO" == stale || ( "$SCENARIO" == delayed && "$LOG_READS" == 1 ) ]]; then
    token=stale
  fi
  [[ "$SCENARIO" == stock ]] && map=cp_dustbowl
  [[ "$SCENARIO" == pending ]] && state=downloading
  printf 'BEGIN-%s\n454299390 workshop/cp_orange_x3.ugc454299390 %s\nmap : %s at: 0 x, 0 y, 0 z\n' "$token" "$state" "$map"
  if [[ "$SCENARIO" == incomplete || ( "$SCENARIO" == delayed && "$LOG_READS" == 2 ) ]]; then
    return 0
  fi
  printf 'END-%s\n' "$token"
}
'''
    command = 'capture_native_workshop_probe' + (' --ready-only' if ready_only else '')
    result = subprocess.run(
        ['bash', '-c', probe + fake_console + '\nif ' + command + '; then result=0; else result=$?; fi\n'
         + '''printf '{"result":%s,"sends":%s,"reads":%s}\\n' "$result" "$SEND_COUNT" "$LOG_READS"'''],
        env=dict(os.environ, REPO_ROOT=str(REPO_ROOT), PYTHON_BIN=sys.executable,
                 SERVER_NAME='tf2', WORK_DIR=str(tmp_path), WORKSHOP_ITEM='454299390',
                 WORKSHOP_MAP='cp_orange_x3', WORKSHOP_DEADLINE=str(deadline), SCENARIO=scenario),
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout.splitlines()[-1])
    passed = scenario == 'delayed' or (scenario == 'stock' and ready_only)
    assert observed == {
        'result': 0 if passed else 1,
        'sends': 1,
        'reads': (3 if scenario == 'delayed' else 1) if passed else min(deadline, 15),
    }
