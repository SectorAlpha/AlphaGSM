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
