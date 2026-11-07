"""Exercise Minecraft's integration lifecycle with CLI-only unit fixtures."""

import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    calls = []
    monkeypatch.setattr(helpers, "pick_free_tcp_port", lambda: calls.append("port") or 24567)
    def readiness(_env, name, protocol, timeout, expected_port):
        assert (name, protocol, timeout, expected_port) == ("itmc", "slp", 180, 24567)
        calls.append("readiness")
        return {"protocol": "slp", "port": 24567, "version": "1.21.8"}

    monkeypatch.setattr(helpers, "wait_for_info_protocol", readiness)
    monkeypatch.setattr(helpers, "wait_for_tcp_closed", lambda *_args: calls.append("closed"))
    monkeypatch.setattr(helpers, "require_command_for_runtime", lambda *_args, **_kwargs: None)
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    path = Path(__file__).resolve().parents[1] / "integration_tests" / "test_minecraft_vanilla.py"
    spec = importlib.util.spec_from_file_location("minecraft_vanilla_lifecycle_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "_require_integration_opt_in", lambda: None)
    monkeypatch.setattr(module, "_require_command", lambda _name: None)
    monkeypatch.setattr(module, "_write_config", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "_alphagsm_env", lambda _path: {})
    monkeypatch.setattr(module, "_fetch_latest_release_server_url", lambda: ("1.21.8", "https://example.invalid/server.jar"))
    monkeypatch.setattr(module, "_pick_free_port", lambda: 24567, raising=False)
    monkeypatch.setattr(module, "_wait_for_status", lambda *_args: pytest.fail("Direct loopback readiness must not run"), raising=False)
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", "docker")

    def run(_env, _name, command, *args, **_kwargs):
        calls.append(command)
        if command == "setup":
            installation = tmp_path / "minecraft-server"
            installation.mkdir()
            for name in ("minecraft_server.jar", "eula.txt", "server.properties"):
                (installation / name).touch()
        if command == "info":
            output = json.dumps({"protocol": "slp", "players_online": 0, "players_max": 20}) if args else (
                "Server info (SLP)\nPlayers     : 0/20")
        elif command == "status":
            output = "Server isn't running" if "stop" in calls else "Server is running"
        else:
            output = "Server port is open" if command == "query" else "ok"
        return subprocess.CompletedProcess([command], 0, output, "")

    monkeypatch.setattr(module, "run_alphagsm", run)
    # Shared cleanup resolves its CLI from the helper module, as in real runs.
    monkeypatch.setattr(helpers, "run_alphagsm", run)
    return module, helpers, calls, run


def test_successful_lifecycle_uses_shared_port_and_slp_readiness(lifecycle, tmp_path):
    module, _helpers, calls, _run = lifecycle
    module.test_minecraft_vanilla_download_install_and_start(tmp_path)
    assert calls == ["port", "create", "set", "setup", "start", "readiness", "status", "message",
                     "query", "info", "info", "stop", "closed", "status"]


@pytest.mark.parametrize("error_type", [AssertionError, pytest.fail.Exception])
def test_cleanup_failure_does_not_replace_original_readiness_failure(lifecycle, tmp_path, monkeypatch, error_type):
    module, helpers, calls, run = lifecycle
    original = error_type("original readiness failure")

    def readiness(*_args, **_kwargs):
        raise original

    def failing_stop(*args, **kwargs):
        if args[2] == "stop":
            calls.append("stop")
            raise subprocess.TimeoutExpired(["stop"], 90)
        return run(*args, **kwargs)

    monkeypatch.setattr(module, "wait_for_info_protocol", readiness, raising=False)
    monkeypatch.setattr(module, "run_alphagsm", failing_stop)
    monkeypatch.setattr(helpers, "run_alphagsm", failing_stop)
    with pytest.raises(error_type) as failure:
        module.test_minecraft_vanilla_download_install_and_start(tmp_path)
    assert failure.value is original
    assert calls[-1] == "stop"
    assert "closed" not in calls


@pytest.mark.parametrize("failed_check", ["closed", "status"])
def test_successful_stop_still_requires_closed_port_and_stopped_status(lifecycle, tmp_path, monkeypatch, failed_check):
    module, _helpers, _calls, run = lifecycle

    if failed_check == "closed":
        def fail_close(*_args):
            raise AssertionError("port is still open")
        monkeypatch.setattr(module, "wait_for_tcp_closed", fail_close)
    else:
        def running_status(*args, **kwargs):
            result = run(*args, **kwargs)
            if args[2] == "status":
                result.stdout = "Server is running"
            return result
        monkeypatch.setattr(module, "run_alphagsm", running_status)
    with pytest.raises(AssertionError):
        module.test_minecraft_vanilla_download_install_and_start(tmp_path)


def test_successful_readiness_still_requires_successful_stop(lifecycle, tmp_path, monkeypatch):
    module, helpers, calls, run = lifecycle

    def failing_stop(*args, **kwargs):
        if args[2] == "stop":
            calls.append("stop")
            return subprocess.CompletedProcess(["stop"], 1, "", "shutdown failed")
        return run(*args, **kwargs)

    monkeypatch.setattr(module, "run_alphagsm", failing_stop)
    monkeypatch.setattr(helpers, "run_alphagsm", failing_stop)
    with pytest.raises(AssertionError, match="shutdown failed"):
        module.test_minecraft_vanilla_download_install_and_start(tmp_path)
    assert "closed" not in calls
