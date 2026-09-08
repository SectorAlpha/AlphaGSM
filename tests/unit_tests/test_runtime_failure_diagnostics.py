"""Bounded, read-only evidence for Docker startup stalls."""

import importlib
import json
import re
import subprocess
from pathlib import Path

import pytest


def _helpers():
    return importlib.import_module("tests.integration_tests.runtime_diagnostics")


def test_process_probe_captures_wait_state_without_command_or_environment(tmp_path):
    helpers = _helpers()
    proc = tmp_path / "proc"
    process = proc / "31"
    (process / "fd").mkdir(parents=True)
    (process / "task" / "32").mkdir(parents=True)
    (process / "comm").write_text("srcds_linux\n")
    (process / "status").write_text("Name:\tsrcds_linux\nState:\tS (sleeping)\nUid:\t1001\t1001\t1001\t1001\n")
    (process / "wchan").write_text("futex_wait_queue")
    (process / "task" / "32" / "wchan").write_text("pipe_read")
    (process / "fd" / "0").symlink_to("/tmp/alphagsm-console.fifo")
    (process / "cmdline").write_bytes(b"srcds\0password=never-read\0")
    (process / "environ").write_bytes(b"TOKEN=never-read\0")
    result = helpers.collect_process_diagnostics(proc_root=proc, home_roots=[])

    row = result["processes"][0]
    assert row["comm"] == "srcds_linux"
    assert row["wchan"] == "futex_wait_queue"
    assert row["stdin"] == "/tmp/alphagsm-console.fifo"
    assert row["threads"] == [{"tid": 32, "wchan": "pipe_read"}]
    assert "never-read" not in json.dumps(result)


def test_process_probe_bounds_logs_and_ignores_steam_credentials(tmp_path):
    helpers = _helpers()
    home = tmp_path / "home"
    logs = home / ".steam" / "steam" / "logs"
    logs.mkdir(parents=True)
    (logs / "connection_log.txt").write_text("old-line\n" * 200 + "last-line\n")
    (logs / "loginusers.vdf").write_text("credential-never-read")
    result = helpers.collect_process_diagnostics(proc_root=tmp_path / "missing", home_roots=[home])

    assert result["processes"] == []
    assert len(result["steam_logs"]) == 1
    assert result["steam_logs"][0]["tail"].endswith("last-line\n")
    assert len(result["steam_logs"][0]["tail"].splitlines()) <= 30
    assert "credential-never-read" not in json.dumps(result)
    assert {
        "path": str(home / ".steam/steam/steamapps/libraryfolders.vdf"),
        "exists": False,
    } in result["steam_state"]


def test_stopped_container_retains_exit_evidence_without_exec():
    helpers = _helpers()
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, '{"Status":"exited","Running":false,"ExitCode":137,"OOMKilled":true}', "")

    results = helpers.collect_docker_runtime_diagnostics("alphagsm-test", run_command=run)
    assert len(results) == 1
    assert json.loads(results[0][1].stdout)["OOMKilled"] is True
    assert len(calls) == 1
    assert calls[0][1]["timeout"] == 10


def test_live_container_uses_bounded_readonly_probe():
    helpers = _helpers()
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        output = '{"Running":true}' if len(calls) == 1 else '{"processes":[]}'
        return subprocess.CompletedProcess(command, 0, output, "")

    results = helpers.collect_docker_runtime_diagnostics("alphagsm-test", run_command=run)
    assert len(results) == 2
    assert calls[1][0][:5] == ["docker", "exec", "alphagsm-test", "python3", "-c"]
    assert all(kwargs["timeout"] == 10 for _, kwargs in calls)
    assert all(kwargs["check"] is False for _, kwargs in calls)
    compile(calls[1][0][-1], "container-probe", "exec")


def test_diagnostic_timeout_is_returned_as_evidence():
    helpers = _helpers()

    def run(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 10, output=b"partial state")

    results = helpers.collect_docker_runtime_diagnostics("alphagsm-test", run_command=run)
    assert len(results) == 1
    assert results[0][1].returncode != 0
    assert "timed out" in results[0][1].stderr
    assert results[0][1].stdout == "partial state"


@pytest.mark.parametrize("error", [FileNotFoundError("docker unavailable"), PermissionError("socket denied")])
def test_unavailable_docker_is_returned_as_evidence(error):
    helpers = _helpers()

    def run(_command, **_kwargs):
        raise error

    results = helpers.collect_docker_runtime_diagnostics("alphagsm-test", run_command=run)
    assert len(results) == 1
    assert results[0][1].returncode == 1
    assert str(error) in results[0][1].stderr


def test_exec_timeout_retains_container_state():
    helpers = _helpers()
    calls = []

    def run(command, **_kwargs):
        calls.append(command)
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 0, '{"Running":true}', "")
        raise subprocess.TimeoutExpired(command, 10)

    results = helpers.collect_docker_runtime_diagnostics("alphagsm-test", run_command=run)
    assert len(results) == 2
    assert results[0][1].returncode == 0
    assert results[1][1].returncode == 124


@pytest.mark.parametrize("times_out", [False, True])
def test_source_stack_probe_is_isolated_and_always_cleaned_up(monkeypatch, times_out):
    helpers = _helpers()
    monkeypatch.setenv("ALPHAGSM_DIAGNOSTIC_IMAGE", "ci-image:fixture")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1] == "inspect":
            output = '{"Running":true}'
        elif command[1] == "exec":
            output = '{"processes":[{"pid":34,"comm":"srcds_linux"}]}'
        elif command[1] == "run":
            if times_out:
                raise subprocess.TimeoutExpired(command, 30)
            output = "Steam frame without arguments"
        else:
            output = ""
        return subprocess.CompletedProcess(command, 0, output, "")

    results = helpers.collect_docker_runtime_diagnostics("alphagsm-test", run_command=run)
    stack_calls = [command for command, _kwargs in calls if command[1] == "run"]
    assert len(stack_calls) == 1
    command = stack_calls[0]
    assert command[command.index("--pid") + 1] == "container:alphagsm-test"
    assert command[command.index("--network") + 1] == "none"
    assert command[command.index("--cap-drop") + 1] == "ALL"
    assert command[command.index("--cap-add") + 1] == "SYS_PTRACE"
    assert "--read-only" in command
    assert "--privileged" not in command
    assert "seccomp=unconfined" not in command
    name = command[command.index("--name") + 1]
    assert name.startswith("alphagsm-diagnostic-")
    assert calls[-1][0] == ["docker", "rm", "-f", name]
    assert results[-1][1].returncode == (124 if times_out else 0)
    compile(command[-1], "stack-probe", "exec")


def test_stack_probe_disables_debugger_execution_and_argument_output(tmp_path, monkeypatch):
    helpers = _helpers()
    process = tmp_path / "34"
    process.mkdir()
    (process / "comm").write_text("srcds_linux\n")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "#0 SteamAPI_Init ()", "")

    monkeypatch.setattr(helpers.subprocess, "run", run)
    result = helpers.collect_source_stacks(proc_root=tmp_path)
    assert len(result) == 1
    command, kwargs = calls[0]
    assert "-nx" in command and "-nh" in command
    assert "set auto-load off" in command
    assert "set print frame-arguments none" in command
    assert "thread apply all bt 12" in command
    assert "detach" in command
    assert kwargs["timeout"] == 8


def test_ci_debugger_image_survives_switch_to_test_user():
    workflow = Path(".github/workflows/unittest.yaml").read_text()
    for job in ("integration-test-standard", "integration-test-heavy", "integration-flake-recheck"):
        # Find the complete job block by its next top-level job key.
        block = re.split(r"\n  [a-z][a-z-]+:", workflow.split("\n  " + job + ":", 1)[1], maxsplit=1)[0]
        assert "ALPHAGSM_DIAGNOSTIC_IMAGE: ${{ needs.build-integration-image.outputs.image }}" in block
        assert "export ALPHAGSM_DIAGNOSTIC_IMAGE=" in block
