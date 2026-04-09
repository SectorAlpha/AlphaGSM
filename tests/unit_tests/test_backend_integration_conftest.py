"""Unit tests for backend integration helper behaviour."""

import json
import os
from types import SimpleNamespace

import pytest

from tests.helpers import load_module_from_repo


backend_conftest = load_module_from_repo(
    "backend_integration_conftest",
    "tests/backend_integration_tests/conftest.py",
)


def test_backend_run_and_assert_ok_fails_instead_of_skipping_known_issue(monkeypatch):
    result = SimpleNamespace(
        returncode=1,
        stdout="Error extracting download",
        stderr="returned non-zero exit status",
    )

    monkeypatch.setattr(backend_conftest, "_run_alphagsm", lambda env, *args, timeout=None: result)
    monkeypatch.setattr(backend_conftest, "_log_command_result", lambda *args, **kwargs: None)

    with pytest.raises(AssertionError):
        backend_conftest._run_and_assert_ok({}, "demo", "setup")


def test_backend_wait_for_closed_fails_when_port_never_closes(monkeypatch):
    result = SimpleNamespace(
        returncode=1,
        stdout="still open",
        stderr="",
    )

    monkeypatch.setattr(backend_conftest.subprocess, "run", lambda *args, **kwargs: result)
    monkeypatch.setattr(backend_conftest, "_log_command_result", lambda *args, **kwargs: None)

    with pytest.raises(pytest.fail.Exception):
        backend_conftest._wait_for_closed("127.0.0.1", 25565, 10)


def test_write_config_can_override_server_module_package(tmp_path):
    config_path = tmp_path / "alphagsm.conf"
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    backend_conftest._write_config(
        config_path,
        home_dir,
        "BkTest#",
        backend="subprocess",
        servermodulespackage="tests.backend_integration_tests.testmodules.",
    )

    config_text = config_path.read_text(encoding="utf-8")
    assert "servermodulespackage = tests.backend_integration_tests.testmodules." in config_text


def test_alphagsm_env_includes_repo_root_and_src(tmp_path):
    env = backend_conftest._alphagsm_env(tmp_path / "alphagsm.conf")

    pythonpath_entries = env["PYTHONPATH"].split(os.pathsep)
    assert str(backend_conftest.REPO_ROOT) in pythonpath_entries
    assert str(backend_conftest.REPO_ROOT / "src") in pythonpath_entries


def test_load_server_data_reads_expected_json(tmp_path):
    home_dir = tmp_path / "home"
    conf_dir = home_dir / "conf"
    conf_dir.mkdir(parents=True)
    expected = {"port": 27015, "queryport": 27016}
    (conf_dir / "alpha.json").write_text(json.dumps(expected), encoding="utf-8")

    assert backend_conftest._load_server_data(home_dir, "alpha") == expected


def test_bind_tcp_listener_claims_requested_port(monkeypatch):
    events = []

    class FakeSocket:
        def setsockopt(self, level, option, value):
            events.append(("setsockopt", level, option, value))

        def bind(self, address):
            events.append(("bind", address))

        def listen(self, backlog):
            events.append(("listen", backlog))

    monkeypatch.setattr(backend_conftest.socket, "socket", lambda *args, **kwargs: FakeSocket())

    listener = backend_conftest._bind_tcp_listener("127.0.0.1", 25565)

    assert isinstance(listener, FakeSocket)
    assert ("bind", ("127.0.0.1", 25565)) in events
    assert ("listen", 5) in events


def test_wait_for_tcp_open_fails_when_port_never_opens(monkeypatch):
    ticks = iter([0.0, 0.3, 0.6, 1.1])

    monkeypatch.setattr(
        backend_conftest.socket,
        "create_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("still closed")),
    )
    monkeypatch.setattr(backend_conftest.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(backend_conftest.time, "sleep", lambda *_args, **_kwargs: None)

    with pytest.raises(pytest.fail.Exception):
        backend_conftest._wait_for_tcp_open("127.0.0.1", 25565, 1)
