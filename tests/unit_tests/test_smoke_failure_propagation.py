"""Check smoke command failures propagate through actual shell control flow."""
import os
from pathlib import Path
import subprocess

import pytest

from tests.helpers import REPO_ROOT


@pytest.mark.parametrize('command', ['wait-for-status', 'wait-for-closed'])
def test_minecraft_readiness_and_shutdown_timeouts_fail(tmp_path, command):
    helper = tmp_path / 'fake-python'
    helper.write_text('#!/bin/bash\n[[ "$2" != "$FAIL_COMMAND" ]]\n')
    helper.chmod(0o755)
    script = (REPO_ROOT / 'tests/smoke_tests/run_minecraft_vanilla.sh').read_text()
    lifecycle = script[script.index('run_alphagsm "$SERVER_NAME" start'):]
    prelude = ('set -Eeuo pipefail\nrun_alphagsm() { :; }\nSERVER_NAME=test\n'
               'STATUS_HELPER=unused\nPORT=1234\nSTART_TIMEOUT_SECONDS=0\nSTOP_TIMEOUT_SECONDS=0\n')
    result = subprocess.run(['bash', '-c', prelude + lifecycle], check=False, capture_output=True,
                            env=dict(os.environ, PYTHON_BIN=str(helper), FAIL_COMMAND=command))
    assert result.returncode != 0


def test_make_all_smoke_runs_remaining_tests_but_returns_failure(tmp_path):
    smoke_dir = tmp_path / 'tests/smoke_tests'
    smoke_dir.mkdir(parents=True)
    for name, command in [('a', 'exit 1'), ('b', 'touch remaining-ran'), ('c', 'exit 77')]:
        (smoke_dir / f'run_{name}.sh').write_text(command + '\n')
    makefile = (REPO_ROOT / 'Makefile').read_text()
    recipe = makefile[makefile.index('smoke-test:\n'):].split('\n\n', 1)[0]
    (tmp_path / 'Makefile').write_text(recipe + '\n')
    result = subprocess.run(['make', 'smoke-test'], cwd=tmp_path, capture_output=True, check=False)
    assert (tmp_path / 'remaining-ran').exists()
    assert result.returncode != 0


def test_make_all_smoke_accepts_deliberate_skip(tmp_path):
    smoke_dir = tmp_path / 'tests/smoke_tests'
    smoke_dir.mkdir(parents=True)
    (smoke_dir / 'run_skip.sh').write_text('exit 77\n')
    makefile = (REPO_ROOT / 'Makefile').read_text()
    (tmp_path / 'Makefile').write_text(makefile[makefile.index('smoke-test:\n'):].split('\n\n', 1)[0] + '\n')
    result = subprocess.run(['make', 'smoke-test'], cwd=tmp_path, capture_output=True, check=False)
    assert result.returncode == 0
