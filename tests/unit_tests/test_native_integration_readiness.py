"""Replay affected CI lifecycles without launching processes or game servers."""

import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


CASES = (
    ("pcarserver", "a2s", 27016, None),
    ("silicaserver", "a2s", 27016, None),
    ("solserver", "soldat", 27025, None),
    ("groundbranchserver", "udp", 27015, None),
    ("argoserver", "a2s", 27016, None),
    ("lifeisfeudalserver", "a2s", 27017, None),
    ("q2server", "quake2", 27015, b"\xff\xff\xff\xffstatus\n"),
    ("qwserver", "quakeworld", 27015, b"\xff\xff\xff\xffstatus\n"),
    ("unturned", "a2s", 27015, None),
    ("pixarkserver", "a2s", 27016, None),
    ("kf2server", "a2s", 28015, None),
    ("conanexiles", "a2s", 28015, None),
    ("codwawserver", "quake", 27015, b"\xff\xff\xff\xffgetstatus\n"),
    ("icarusserver", "tcp", 27015, None),
    ("notdserver", "tcp", 27015, None),
    ("noonesurvivedserver", "tcp", 27015, None),
    ("soulmask", "tcp", 27015, None),
    ("ets2server", "a2s", 28015, None),
    ("stnserver", "a2s", 27016, None),
)


@pytest.fixture(params=CASES, ids=[case[0] for case in CASES])
def lifecycle(request, monkeypatch, tmp_path):
    name, protocol, query_port, shutdown_payload = request.param
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setitem(sys.modules, "conftest", helpers)
    path = Path(__file__).resolve().parents[1] / "integration_tests" / f"test_{name}.py"
    spec = importlib.util.spec_from_file_location(f"native_{name}_fixture", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []
    for hook in ("require_integration_opt_in", "require_steamcmd_opt_in", "require_command",
                 "require_command_for_runtime", "require_proton", "write_config"):
        monkeypatch.setattr(module, hook, lambda *_a, **_kw: None, raising=False)
    monkeypatch.setattr(module, "resolve_runtime_image", lambda *_a: "fixture-image", raising=False)
    monkeypatch.setattr(module, "resolve_steamcmd_linux_runtime_image", lambda: "fixture-image", raising=False)
    monkeypatch.setattr(module, "_docker_rm_force", lambda _name: None, raising=False)
    monkeypatch.setattr(module, "alphagsm_env", lambda _path: {})
    tcp_ports = iter(range(27015, 27025))
    monkeypatch.setattr(module, "pick_free_tcp_port", lambda: next(tcp_ports), raising=False)
    monkeypatch.setattr(module, "pick_free_tcp_port_group", lambda _count: 27015, raising=False)
    udp_ports = iter((28015, 28016))
    monkeypatch.setattr(module, "pick_free_udp_port", lambda: next(udp_ports), raising=False)
    monkeypatch.setattr(module, "effective_runtime_backend", lambda backend, **_kw: backend, raising=False)
    monkeypatch.setattr(module, "default_runtime_backend", lambda: "process")
    monkeypatch.setattr(module, "detect_query_host", lambda: "127.0.0.1", raising=False)
    if name == "ets2server":
        exports = tmp_path / "exports"
        exports.mkdir()
        for filename in ("server_packages.sii", "server_packages.dat"):
            (exports / filename).write_bytes(b"fixture")
        monkeypatch.setenv("ALPHAGSM_ETS2_SERVER_PACKAGES_DIR", str(exports))

    def run(_env, _name, command, *args, **_kwargs):
        calls.append(command)
        if command == "info":
            if args:
                output = json.dumps(
                    {
                        "protocol": protocol,
                        "port": query_port,
                        "players": 0,
                        "name": "AlphaGSM Conan IT",
                        "map": "fixture",
                    }
                )
            elif protocol in ("tcp", "udp"):
                output = f"{protocol.upper()} ping on port\nNo further details available."
            else:
                output = (
                    "Server info (A2S on port) Server info (Quake on port)\n"
                    "Name        : AlphaGSM Conan IT\nPlayers     : 0/16"
                )
        elif command == "query":
            if protocol in ("tcp", "udp"):
                output = f"{protocol.upper()} ping on port"
            else:
                label = "Quake" if protocol == "quake" else "A2S"
                output = f"Server is responding ({label} on port)"
        elif command == "status":
            output = "Server isn't running" if "stop" in calls else "Server is running"
        else:
            output = "ok"
        return subprocess.CompletedProcess([command], 0, output, "")

    monkeypatch.setattr(module, "run_alphagsm", run, raising=False)
    monkeypatch.setattr(helpers, "run_alphagsm", run)
    monkeypatch.setattr(module, "run_setup_with_port_retry",
                        lambda env, server, port, *_a, **kw: (run(env, server, "setup"), port),
                        raising=False)

    def readiness(_env, _server, actual_protocol, _timeout, expected_port=None):
        assert (actual_protocol, expected_port) == (protocol, query_port)
        calls.append("readiness")
        return {"protocol": protocol, "port": query_port, "players": 0}

    def closed(_host, port, _timeout, payload=None):
        assert port == query_port
        assert payload == shutdown_payload
        calls.append("closed")

    monkeypatch.setattr(module, "wait_for_info_protocol", readiness, raising=False)
    monkeypatch.setattr(module, "wait_for_udp_closed", closed, raising=False)
    monkeypatch.setattr(module, "wait_for_generic_udp_closed", closed, raising=False)
    for hook in ("wait_for_tcp_closed", "wait_for_runtime_log_marker", "wait_for_log_marker",
                 "wait_for_quake2_ready", "wait_for_quakeworld_ready", "wait_for_a2s_ready",
                 "wait_for_udp_open"):
        monkeypatch.setattr(module, hook, lambda *_a, **_kw: pytest.fail("obsolete probe called"),
                            raising=False)
    if name == "groundbranchserver":
        def groundbranch_log_ready(_path, markers, _timeout, **_kwargs):
            assert markers == (f"started listening on {query_port}",)
            calls.append("log-readiness")

        monkeypatch.setattr(module, "wait_for_log_marker", groundbranch_log_ready)
    if name == "lifeisfeudalserver":
        monkeypatch.setattr(module, "wait_for_tcp_closed", lambda *_a: calls.append("db-closed"))
    if name == "solserver":
        monkeypatch.setattr(module, "wait_for_tcp_closed", closed)
    if name == "soulmask":
        monkeypatch.setattr(module, "wait_for_tcp_closed", closed)
    if name == "icarusserver":
        monkeypatch.setattr(module, "wait_for_tcp_closed", closed)
    if name == "notdserver":
        monkeypatch.setattr(module, "wait_for_tcp_closed", closed)
    if name == "noonesurvivedserver":
        monkeypatch.setattr(module, "wait_for_tcp_closed", closed)
    return module, helpers, calls, run


@pytest.mark.parametrize("backend", ["process", "docker"])
def test_lifecycle_uses_native_readiness_and_matching_shutdown(lifecycle, tmp_path, monkeypatch, backend):
    module, _helpers, calls, _run = lifecycle
    monkeypatch.setenv("ALPHAGSM_TEST_RUNTIME_BACKEND", backend)
    monkeypatch.setattr(module, "runtime_backend", backend, raising=False)
    next(value for key, value in vars(module).items() if key.startswith("test_"))(tmp_path)
    assert calls.index("start") < calls.index("readiness") < calls.index("query")
    if module.module_name == "groundbranchserver":
        assert calls.index("start") < calls.index("log-readiness") < calls.index("readiness")
    assert calls.index("query") < calls.index("stop") < calls.index("closed")


def test_readiness_error_survives_failed_cleanup(lifecycle, tmp_path, monkeypatch):
    module, helpers, calls, run = lifecycle
    original = pytest.fail.Exception("native readiness failed")

    def not_ready(*_args, **_kwargs):
        raise original

    def failing_stop(*args, **kwargs):
        if args[2] == "stop":
            calls.append("stop")
            raise subprocess.TimeoutExpired(["stop"], 90)
        return run(*args, **kwargs)

    monkeypatch.setattr(module, "wait_for_info_protocol", not_ready)
    monkeypatch.setattr(module, "run_alphagsm", failing_stop, raising=False)
    monkeypatch.setattr(helpers, "run_alphagsm", failing_stop)
    with pytest.raises(pytest.fail.Exception) as failure:
        next(value for key, value in vars(module).items() if key.startswith("test_"))(tmp_path)
    assert failure.value is original
    assert calls[-1] == "stop"


def test_successful_readiness_cannot_hide_failed_stop(lifecycle, tmp_path, monkeypatch):
    module, helpers, calls, run = lifecycle

    def failing_stop(*args, **kwargs):
        if args[2] == "stop":
            calls.append("stop")
            return subprocess.CompletedProcess(["stop"], 1, "", "shutdown failed")
        return run(*args, **kwargs)

    monkeypatch.setattr(module, "run_alphagsm", failing_stop, raising=False)
    monkeypatch.setattr(helpers, "run_alphagsm", failing_stop)
    with pytest.raises(AssertionError, match="shutdown failed"):
        next(value for key, value in vars(module).items() if key.startswith("test_"))(tmp_path)
    assert "closed" not in calls
