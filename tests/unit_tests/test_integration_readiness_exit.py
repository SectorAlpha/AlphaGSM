"""Readiness polls distinguish confirmed exits from unavailable diagnostics."""

import importlib
import json
import subprocess

import pytest


def doctor(runtime, **extra):
    return {"schema_version": 1, "server": "fixture", "runtime": runtime, **extra}


STOPPED = {"resolved_runtime": "docker", "running": False,
           "container_state": "stopped", "container_name": "fixture"}


@pytest.fixture
def harness(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    clock = [0.0]
    calls = []
    events = []
    monkeypatch.setattr(helpers.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(helpers.time, "time", lambda: clock[0])
    monkeypatch.setattr(helpers.time, "sleep", lambda delay: clock.__setitem__(0, clock[0] + delay))
    monkeypatch.setattr(helpers, "_dump_alphagsm_runtime_logs", lambda *_args: events.append("runtime diagnostics"))

    def install(reports, ready_after=None, probe_timeout=False):
        reports = iter(reports)
        probe_count = [0]

        def run(_env, _server, command, *_args, timeout, **_kwargs):
            calls.append((command, timeout, clock[0]))
            assert 0 < timeout <= 600 - clock[0]
            clock[0] += min(0.1, timeout)
            if command == "doctor":
                report = next(reports, doctor({"inspection_error": "temporarily unavailable"}))
                if isinstance(report, Exception):
                    raise report
                if isinstance(report, subprocess.CompletedProcess):
                    return report
                output = json.dumps(report) if not isinstance(report, str) else report
                return subprocess.CompletedProcess([command], 0, output, "")
            probe_count[0] += 1
            if probe_timeout:
                clock[0] += timeout - 0.1
                raise subprocess.TimeoutExpired([command], timeout, output=b"password=poll-secret")
            ready = ready_after is not None and probe_count[0] >= ready_after
            output = json.dumps({"protocol": "a2s" if ready else "unknown"}) if command == "info" else (
                "fixture ready" if ready else "startup refused: token=log-secret")
            return subprocess.CompletedProcess([command], 0, output, "")

        monkeypatch.setattr(helpers, "run_alphagsm", run)

    return helpers, clock, calls, events, install


def wait(helpers, kind, timeout=600):
    if kind == "info":
        return helpers.wait_for_info_protocol({}, "fixture", "a2s", timeout)
    return helpers.wait_for_runtime_log_marker({}, "fixture", ["fixture ready"], timeout)


@pytest.mark.parametrize("kind", ["info", "logs"])
@pytest.mark.parametrize("runtime", [STOPPED, {"resolved_runtime": "process", "running": False}])
def test_confirmed_exit_fails_before_readiness_deadline(harness, kind, runtime, capsys):
    helpers, clock, calls, events, install = harness
    install([doctor(runtime, token="doctor-secret"), doctor(runtime, token="doctor-secret")])
    with pytest.raises(pytest.fail.Exception, match="exited before readiness"):
        wait(helpers, kind)
    assert clock[0] < 20
    assert [call[0] for call in calls] == [kind, "doctor", kind, "doctor"]
    assert events == ["runtime diagnostics"]
    output = capsys.readouterr().out
    assert "doctor --json" in output
    assert "doctor-secret" not in output
    assert "log-secret" not in output


@pytest.mark.parametrize("kind", ["info", "logs"])
@pytest.mark.parametrize("unknown", [
    doctor({**STOPPED, "docker_daemon_error": "connection refused"}),
    doctor({"resolved_runtime": "docker", "running": False}),
    doctor({**STOPPED, "container_state": "missing"}),
    doctor({**STOPPED, "running": True}),
    doctor({"resolved_runtime": "process", "running": "false"}),
    {"schema_version": 2, "runtime": STOPPED},
    "invalid JSON",
    [],
    subprocess.TimeoutExpired(["doctor"], 10),
    OSError("temporary process inspection failure"),
    subprocess.CompletedProcess(["doctor"], 1, json.dumps(doctor(STOPPED)), "failed inspection"),
])
def test_unknown_state_breaks_stopped_confirmation_and_allows_readiness(harness, kind, unknown):
    helpers, _clock, calls, _events, install = harness
    install([doctor(STOPPED), unknown, doctor(STOPPED)], ready_after=4)
    wait(helpers, kind)
    assert [call[0] for call in calls].count("doctor") == 3


@pytest.mark.parametrize("kind", ["info", "logs"])
def test_probe_timeout_uses_remaining_monotonic_budget(harness, kind, monkeypatch, capsys):
    helpers, clock, calls, events, install = harness
    install([], probe_timeout=True)
    monkeypatch.setattr(helpers.time, "time", lambda: pytest.fail("Readiness must use monotonic time"))
    with pytest.raises(pytest.fail.Exception, match="never"):
        wait(helpers, kind, timeout=0.5)
    assert calls == [(kind, 0.5, 0.0)]
    assert clock[0] == 0.5
    assert events == ["runtime diagnostics"]
    output = capsys.readouterr().out
    assert "poll-secret" not in output
    assert "<redacted>" in output


@pytest.mark.parametrize("kind", ["info", "logs"])
def test_different_container_does_not_confirm_previous_exit(harness, kind):
    helpers, _clock, calls, _events, install = harness
    install([doctor(STOPPED), doctor({**STOPPED, "container_name": "replacement"})], ready_after=3)
    wait(helpers, kind)
    assert [call[0] for call in calls].count("doctor") == 2


def test_readiness_probe_does_not_add_an_unbudgeted_automatic_doctor_call(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs["timeout"]))
        return subprocess.CompletedProcess(command, 1, "not ready", "")

    monkeypatch.setattr(helpers.subprocess, "run", run)
    result = helpers.run_alphagsm({"ALPHAGSM_DIAGNOSTICS_DIR": str(tmp_path)}, "fixture", "info",
                                  "--json", timeout=0.5, capture_diagnostics=False)
    assert result.returncode == 1
    assert len(calls) == 1
    assert calls[0][1] == 0.5
    assert not list(tmp_path.iterdir())


def test_runtime_failure_diagnostics_include_redacted_docker_process_evidence(monkeypatch, capsys):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    diagnostics = importlib.import_module("tests.integration_tests.runtime_diagnostics")
    calls = []
    monkeypatch.setattr(helpers, "_capture_doctor_json", lambda *_args: doctor(STOPPED))
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, "", ""))

    def collect(name):
        calls.append(name)
        return [("Docker processes", subprocess.CompletedProcess([], 0, "root child sleeping", "token=process-secret"))]

    monkeypatch.setattr(diagnostics, "collect_docker_runtime_diagnostics", collect)
    helpers._dump_alphagsm_runtime_logs({}, "fixture")
    assert calls == ["fixture"]
    output = capsys.readouterr().out
    assert "root child sleeping" in output
    assert "process-secret" not in output
    assert "token=<redacted>" in output


def test_doctor_capture_returns_the_sanitized_persisted_payload(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    report = doctor(STOPPED, token="capture-secret")
    monkeypatch.setattr(helpers, "run_alphagsm", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 0, json.dumps(report), ""))
    payload = helpers._capture_doctor_json({"ALPHAGSM_DIAGNOSTICS_DIR": str(tmp_path)}, "fixture", "readiness")
    assert payload == json.loads(next(tmp_path.glob("*.json")).read_text())
    assert payload["runtime"]["container_name"] == "fixture"
    assert "capture-secret" not in repr(payload)


def test_source_timeout_attempts_native_queries_before_stack_capture(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    diagnostics = importlib.import_module("tests.integration_tests.runtime_diagnostics")
    report = doctor(STOPPED)
    report["runtime"]["command"] = ["./srcds_run", "-game", "cstrike"]
    monkeypatch.setattr(helpers, "_capture_doctor_json", lambda *_args: report)
    calls = []

    def run(_env, _server, command, *args, **kwargs):
        calls.append((command, args))
        if command == "query":
            assert kwargs["timeout"] == 15
            raise subprocess.TimeoutExpired("query", 15)
        return subprocess.CompletedProcess([], 0, '{"protocol":"a2s"}', "")

    def collect(_name):
        calls.append(("stacks", ()))
        return []

    monkeypatch.setattr(helpers, "run_alphagsm", run)
    monkeypatch.setattr(diagnostics, "collect_docker_runtime_diagnostics", collect)
    helpers._dump_alphagsm_runtime_logs({}, "fixture")
    assert calls[:3] == [("query", ()), ("info", ("--json",)), ("stacks", ())]
    assert [call[0] for call in calls[-2:]] == ["logs", "doctor"]
