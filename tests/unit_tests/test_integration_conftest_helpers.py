"""Unit tests for integration-test helper behaviour."""

import importlib
from pathlib import Path
import sys
import types

import pytest


def test_wait_for_a2s_ready_fails_even_when_tcp_is_open_and_logs_exist(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic query failure used to drive the timeout path."""

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.a2s_info = lambda host, port, timeout=2.0, phase2_timeout=None: (
        (_ for _ in ()).throw(FakeQueryError("udp timeout"))
    )
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    timestamps = [0.0, 0.0, 10.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 10.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    class _DummyConn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        helpers.socket,
        "create_connection",
        lambda *args, **kwargs: _DummyConn(),
    )

    log_path = tmp_path / "server.log"
    log_path.write_text("Server is hibernating\n", encoding="utf-8")

    dumped = []
    monkeypatch.setattr(
        helpers,
        "_dump_log",
        lambda path, context=None: dumped.append((path, context)),
    )

    with pytest.raises(pytest.fail.Exception, match="A2S on 127.0.0.1:27015 never responded"):
        helpers.wait_for_a2s_ready(
            "127.0.0.1",
            27015,
            5,
            log_path=log_path,
            tcp_port=27015,
        )

    assert dumped == [(log_path, "A2S timeout on port 27015")]


def test_wait_for_udp_open_retries_until_success(monkeypatch):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    import utils

    class FakeQueryError(OSError):
        """Synthetic UDP reachability failure."""

    attempts = []

    def _fake_udp_ping(host, port, timeout=2.0):
        attempts.append((host, port, timeout))
        if len(attempts) < 2:
            raise FakeQueryError("udp timeout")
        return 1.5

    fake_q = types.ModuleType("utils.query")
    fake_q.QueryError = FakeQueryError
    fake_q.udp_ping = _fake_udp_ping
    monkeypatch.setattr(utils, "query", fake_q, raising=False)
    monkeypatch.setitem(sys.modules, "utils.query", fake_q)

    timestamps = [0.0, 0.0, 1.0, 1.0]

    def _fake_time():
        if timestamps:
            return timestamps.pop(0)
        return 1.0

    monkeypatch.setattr(helpers.time, "time", _fake_time)
    monkeypatch.setattr(helpers.time, "sleep", lambda seconds: None)

    helpers.wait_for_udp_open("127.0.0.1", 27015, 5)

    assert len(attempts) == 2


def test_build_integration_tmp_path_uses_work_dir(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.setenv("ALPHAGSM_WORK_DIR", str(tmp_path))

    class _Factory:
        def mktemp(self, name):
            raise AssertionError("mktemp should not be used when ALPHAGSM_WORK_DIR is set")

    result = helpers.build_integration_tmp_path("armarserver", _Factory())

    assert result.parent == tmp_path / "pytest-integration"
    assert result.name.startswith("armarserver-")
    assert result.is_dir()


def test_build_integration_tmp_path_falls_back_to_pytest_factory(monkeypatch, tmp_path):
    helpers = importlib.import_module("tests.integration_tests.conftest")
    monkeypatch.delenv("ALPHAGSM_WORK_DIR", raising=False)

    expected = tmp_path / "fallback"

    class _Factory:
        def mktemp(self, name):
            assert name == "ndserver"
            expected.mkdir()
            return expected

    result = helpers.build_integration_tmp_path("ndserver", _Factory())

    assert result == Path(expected)
