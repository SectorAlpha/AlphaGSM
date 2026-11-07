"""Exercise the whole integration runner with isolated tools and no real cleanup."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

pytestmark = pytest.mark.skipif(os.name == "nt" or shutil.which("bash") is None,
                               reason="The POSIX integration runner requires bash")


def _run_isolated_runner(tmp_path, sessions, list_exit, pytest_exit=0):
    runner = tmp_path / "run_integration_tests.sh"
    shutil.copyfile(Path("run_integration_tests.sh"), runner)
    (tmp_path / "lint.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    tools = tmp_path / "tools"
    tools.mkdir()
    calls = tmp_path / "calls.jsonl"
    # Every potentially destructive/runtime command is a fake. Use the current
    # interpreter directly rather than resolving a fake python from this PATH.
    fake = (
        "#!" + sys.executable + "\n"
        "import json, os, sys\n"
        "name = os.path.basename(sys.argv[0])\n"
        "with open(os.environ['RUNNER_CALLS'], 'a') as handle:\n"
        "    handle.write(json.dumps([name, *sys.argv[1:]]) + '\\n')\n"
        "if name == 'screen' and sys.argv[1:] == ['-ls']:\n"
        "    print(os.environ['RUNNER_SESSIONS'])\n"
        "    sys.exit(int(os.environ['RUNNER_LIST_EXIT']))\n"
        "if name == 'screen':\n"
        "    sys.exit(1)  # Failed quit is also a best-effort cleanup operation.\n"
        "if name == 'pytest':\n"
        "    result = int(os.environ['RUNNER_PYTEST_EXIT'])\n"
        "    print('ss\\n2 skipped' if result == 0 else 'F\\n1 failed')\n"
        "    sys.exit(result)\n"
    )
    for name in ("python", "pytest", "screen", "rm"):
        target = tools / name
        target.write_text(fake)
        target.chmod(0o755)
    env = os.environ.copy()
    env.update({"PATH": str(tools) + os.pathsep + env["PATH"],
                "PYTHON_BIN": str(tools / "python"),
                "ALPHAGSM_WORK_DIR": str(tmp_path / "work"),
                "DEFAULT_INTEGRATION_WORK_DIR": str(tmp_path / "unused-default"),
                "RUNNER_CALLS": str(calls), "RUNNER_SESSIONS": sessions,
                "RUNNER_LIST_EXIT": str(list_exit), "RUNNER_PYTEST_EXIT": str(pytest_exit)})
    result = subprocess.run(["bash", str(runner), "test_dstserver.py"],
                            cwd=tmp_path, env=env, capture_output=True, text=True,
                            timeout=20, check=False)
    return result, [json.loads(line) for line in calls.read_text().splitlines()]


@pytest.mark.parametrize("sessions,list_exit", [
    ("No Sockets found.", 1),
    ("123.Operator-production (Detached)", 0),
])
def test_skipped_integration_file_succeeds_when_no_matching_screen_sessions(tmp_path, sessions, list_exit):
    result, calls = _run_isolated_runner(tmp_path, sessions, list_exit)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 skipped" in result.stdout
    assert "Integration test summary" in result.stdout
    assert "Failed      : 0" in result.stdout
    assert [call for call in calls if call[0] == "screen"] == [["screen", "-ls"]]
    assert any(call[0] == "rm" for call in calls), "Cleanup must use the stub, never real rm"
    assert any(call[:3] == ["python", "-m", "pytest"] for call in calls)


def test_cleanup_quits_only_matching_integration_sessions_and_tolerates_quit_failure(tmp_path):
    sessions = ("123.AlphaGSM-IT#first (Detached)\n"
                "456.Operator-production (Detached)\n"
                "789.AlphaGSM-IT#second (Detached)")
    result, calls = _run_isolated_runner(tmp_path, sessions, 0)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Integration test summary" in result.stdout
    assert [call for call in calls if call[0] == "screen"] == [
        ["screen", "-ls"],
        ["screen", "-S", "AlphaGSM-IT#first", "-X", "quit"],
        ["screen", "-S", "AlphaGSM-IT#second", "-X", "quit"],
    ]


def test_empty_screen_cleanup_does_not_hide_integration_test_failure(tmp_path):
    result, _calls = _run_isolated_runner(tmp_path, "No Sockets found.", 1, pytest_exit=1)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Integration test summary" in result.stdout
    assert "Failed      : 1" in result.stdout
    assert "Failures    :" in result.stdout
