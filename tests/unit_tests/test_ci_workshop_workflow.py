"""Required Workshop validation must reach every CI lane and isolated recheck."""

from pathlib import Path
import re

import pytest
import yaml


@pytest.fixture
def jobs():
    return yaml.load(Path(".github/workflows/unittest.yaml").read_text(encoding="utf-8"),
                     Loader=yaml.BaseLoader)["jobs"]


def step(job, name):
    return next(entry for entry in job["steps"] if entry.get("name") == name)


def user_command(command):
    """Inspect the actual login-shell body, after su discards caller variables."""
    match = re.search(r'(?ms)^\s*su [^\n]* - gsmuser -c "\n(?P<body>.*?)^\s*"\s*$', command)
    assert match is not None, "Integration command must run in the isolated game-server user context"
    return match.group("body")


@pytest.mark.parametrize("runner_class", ["standard", "heavy"])
def test_smoke_lanes_run_each_script_through_required_workshop_wrapper(jobs, runner_class):
    command = step(jobs[f"smoke-test-{runner_class}"], "AlphaGSM Smoke Tests")["run"]
    assert 'for script in ${{ matrix.scripts }}; do' in command
    assert 'if python3 scripts/run_ci_workshop_tests.py bash "./$script"; then' in command
    assert not re.search(r'^\s*if bash\s+"\./\$script"', command, re.MULTILINE)
    assert 'rc=$?' in command
    assert 'echo "FAILED: $script"' in command
    assert 'if [ "$failed" -gt 0 ]; then' in command
    assert 'exit 1' in command


@pytest.mark.parametrize("runner_class", ["standard", "heavy"])
def test_integration_lanes_enable_workshop_inside_isolated_user_shell(jobs, runner_class):
    command = step(jobs[f"integration-test-{runner_class}"], "AlphaGSM Pytest Integration Tests")["run"]
    body = user_command(command)
    assert 'export ALPHAGSM_RUN_INTEGRATION=1' in body
    assert 'export ALPHAGSM_RUN_STEAMCMD=1' in body
    assert "export ALPHAGSM_TEST_RUNTIME_BACKEND='${{ matrix.runtime_backend || 'auto' }}'" in body
    assert 'export PYTHONPATH=.:src' in body
    wrapper = 'python3 scripts/run_ci_workshop_tests.py python3 scripts/run_integration_batch_with_retry.py'
    assert wrapper in body
    assert '--no-retry' in body and '--results-file results.xml' in body
    assert '${{ matrix.files }}' in body
    assert not re.search(r'^\s*python3 scripts/run_integration_batch_with_retry.py', body, re.MULTILINE)
    assert command.index(wrapper) > command.index(' - gsmuser -c "')
    assert 'test_exit=$?' in command and 'exit "$test_exit"' in command


def test_isolated_recheck_keeps_required_workshop_validation_and_original_runtime(jobs):
    command = step(jobs["integration-flake-recheck"],
                   "Recheck failed integration case on a fresh runner")["run"]
    body = user_command(command)
    assert 'ALPHAGSM_RECHECK_NODEID' in command.split(' - gsmuser -c "', 1)[0]
    assert "export ALPHAGSM_TEST_RUNTIME_BACKEND='${{ matrix.runtime_backend }}'" in body
    assert 'python3 scripts/run_ci_workshop_tests.py python3 -m pytest' in body
    assert '--junit-xml=recheck-results.xml' in body
    assert 'ALPHAGSM_RECHECK_NODEID' in body
    assert not re.search(r'^\s*python3 -m pytest', body, re.MULTILINE)


def test_native_windows_lane_is_called_and_required_by_summary(jobs):
    windows = jobs["windows-native-unit"]
    assert windows["uses"] == "./.github/workflows/windows-native-unit.yaml"
    assert "if" not in windows, "Native Windows coverage must not depend on game-file routing"
    summary = jobs["summarize-tests"]
    assert "windows-native-unit" in summary["needs"]
    assert summary["if"] == "${{ !cancelled() }}"
    download = step(summary, "Download all test results")
    assert download["with"]["pattern"] == "*-results-*"
    assert download["with"]["merge-multiple"] == "false"
    validate = step(summary, "Validate required jobs and summarize test results")
    assert validate["env"]["CI_NEEDS_JSON"] == "${{ toJson(needs) }}"


@pytest.mark.parametrize("job_name,step_name", [
    ("unit-test", "AlphaGSM Unit Tests"),
    ("coverage", "AlphaGSM Coverage Report"),
])
def test_linux_unit_lanes_deselect_cases_assigned_to_native_windows(jobs, job_name, step_name):
    job = jobs[job_name]
    assert job["runs-on"] == "ubuntu-latest"
    command = step(job, step_name)["run"]
    assert 'pytest tests/unit_tests -' in command
    assert '-m "not native_windows"' in command
