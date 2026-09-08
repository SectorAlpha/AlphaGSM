"""Exercise Quake Live lifecycle checks without launching a game server."""

import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def lifecycle(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    calls = []
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    path = Path(__file__).resolve().parents[1] / "integration_tests" / "test_qlserver.py"
    spec = importlib.util.spec_from_file_location("qlserver_lifecycle_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("require_integration_opt_in", "require_steamcmd_opt_in", "require_command_for_runtime", "write_config"):
        monkeypatch.setattr(module, name, lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "alphagsm_env", lambda _path: {})
    monkeypatch.setattr(module, "pick_free_tcp_port", lambda: 27960)

    def readiness(_env, name, protocol, timeout, expected_port):
        assert (name, protocol, timeout, expected_port) == ("itqlserver", "quake", 600, 27960)
        calls.append("readiness")
        return {"protocol": "quake", "port": 27960, "players": 0}

    def closed(host, port, timeout, payload):
        assert (host, port, timeout, payload) == ("127.0.0.1", 27960, 90, b"\xff\xff\xff\xffgetstatus\n")
        calls.append("udp closed")

    monkeypatch.setattr(module, "wait_for_info_protocol", readiness, raising=False)
    monkeypatch.setattr(module, "wait_for_generic_udp_closed", closed, raising=False)
    for name in ("wait_for_runtime_log_marker", "wait_for_quake_ready", "wait_for_tcp_closed"):
        monkeypatch.setattr(module, name, lambda *_args, **_kwargs: pytest.fail("Old readiness/closure helper called"), raising=False)

    def run(_env, _name, command, *args, **_kwargs):
        calls.append(command)
        if command == "info":
            output = json.dumps({"protocol": "quake", "port": 27960, "players": 0}) if args else "Players: 0"
        elif command == "status":
            output = "Server isn't running" if "stop" in calls else "Server is running"
        else:
            output = "Server is responding" if command == "query" else "ok"
        return subprocess.CompletedProcess([command], 0, output, "")

    monkeypatch.setattr(module, "run_alphagsm", run)
    monkeypatch.setattr(helpers, "run_alphagsm", run)
    return module, helpers, calls, run


@pytest.mark.parametrize("backend", ["process", "docker"])
def test_lifecycle_checks_real_quake_readiness_and_udp_shutdown(lifecycle, tmp_path, monkeypatch, backend):
    module, _helpers, calls, _run = lifecycle
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", backend)
    module.test_qlserver_lifecycle(tmp_path)
    assert calls == ["create", "setup", "start", "readiness", "status", "query", "info", "info",
                     "stop", "udp closed", "status"]


def test_stop_failure_does_not_replace_readiness_failure(lifecycle, tmp_path, monkeypatch):
    module, helpers, calls, run = lifecycle
    original = pytest.fail.Exception("original Quake readiness failure")

    def readiness(*_args, **_kwargs):
        raise original

    def failing_stop(*args, **kwargs):
        if args[2] == "stop":
            calls.append("stop")
            raise subprocess.TimeoutExpired(["stop"], 90)
        return run(*args, **kwargs)

    monkeypatch.setattr(module, "wait_for_info_protocol", readiness)
    monkeypatch.setattr(module, "run_alphagsm", failing_stop)
    monkeypatch.setattr(helpers, "run_alphagsm", failing_stop)
    with pytest.raises(pytest.fail.Exception) as failure:
        module.test_qlserver_lifecycle(tmp_path)
    assert failure.value is original
    assert calls[-1] == "stop"


def test_successful_readiness_requires_successful_stop(lifecycle, tmp_path, monkeypatch):
    module, helpers, _calls, run = lifecycle

    def failing_stop(*args, **kwargs):
        if args[2] == "stop":
            return subprocess.CompletedProcess(["stop"], 1, "", "shutdown failed")
        return run(*args, **kwargs)

    monkeypatch.setattr(module, "run_alphagsm", failing_stop)
    monkeypatch.setattr(helpers, "run_alphagsm", failing_stop)
    with pytest.raises(AssertionError, match="shutdown failed"):
        module.test_qlserver_lifecycle(tmp_path)
