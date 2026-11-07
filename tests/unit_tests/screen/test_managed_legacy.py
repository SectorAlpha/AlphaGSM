"""Preserve PID-file sessions when upgrading to the supervised backend."""

import json
from pathlib import Path

import pytest

from screen.backend import ProcessError
from screen.managed_subprocess import ManagedSubprocessBackend


@pytest.fixture
def backend(tmp_path, monkeypatch):
    import screen.subprocess_backend as legacy

    monkeypatch.setattr(legacy, "_processes", {})
    instance = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    Path(instance._pidfile("old")).write_text("4321", encoding="utf-8")
    monkeypatch.setattr(instance, "_is_pid_alive", lambda pid: pid == 4321)
    return instance


def test_legacy_pid_remains_visible_after_upgrade(backend):
    assert backend.is_running("old")
    assert list(backend.list_sessions()) == ["old"]


def test_legacy_pid_blocks_duplicate_managed_start(backend, monkeypatch):
    import screen.managed_subprocess as managed

    def unexpected_launch(*_args, **_kwargs):
        pytest.fail("A live legacy session must prevent launching a supervisor")

    monkeypatch.setattr(managed.subprocess, "Popen", unexpected_launch)
    with pytest.raises(ProcessError, match="already running"):
        backend.start("old", ["unused"])
    assert not backend._session_path("old").exists()


def test_legacy_kill_uses_pid_and_removes_tracking(backend, monkeypatch):
    killed = []
    monkeypatch.setattr(backend, "_force_kill_process_group", killed.append)
    backend.kill("old")
    assert killed == [4321]
    assert not Path(backend._pidfile("old")).exists()


def test_legacy_input_retains_cross_invocation_error(backend):
    with pytest.raises(ProcessError, match="started by another invocation"):
        backend.send_input("old", "save\n")


def test_legacy_ctrl_c_retains_signal_control(backend, monkeypatch):
    import screen.subprocess_backend as legacy

    signals = []
    monkeypatch.setattr(legacy, "IS_WINDOWS", False)
    monkeypatch.setattr(legacy.os, "kill", lambda pid, signal: signals.append((pid, signal)))
    backend.send_input("old", "\003")
    assert signals == [(4321, legacy.signal.SIGINT)]


def test_stale_legacy_pid_is_cleaned(backend, monkeypatch):
    monkeypatch.setattr(backend, "_is_pid_alive", lambda _pid: False)
    assert not backend.is_running("old")
    assert not Path(backend._pidfile("old")).exists()


def test_existing_managed_state_never_falls_back_to_legacy_pid(backend, monkeypatch):
    backend._session_path("old").mkdir()
    killed = []
    monkeypatch.setattr(backend, "_force_kill_process_group", killed.append)
    assert not backend.is_running("old")
    assert list(backend.list_sessions()) == []
    with pytest.raises(ProcessError, match="supervisor"):
        backend.kill("old")
    with pytest.raises(ProcessError, match="supervisor"):
        backend.send_input("old", "\003")
    assert killed == []
    assert Path(backend._pidfile("old")).exists()


def test_session_listing_merges_and_deduplicates_legacy_and_managed(backend, monkeypatch):
    for name in ("old", "new"):
        session = backend._session_path(name)
        session.mkdir()
        (session / "request.json").write_text(json.dumps({"name": name}), encoding="utf-8")
    Path(backend._pidfile("legacy-only")).write_text("4321", encoding="utf-8")
    monkeypatch.setattr(backend, "_request", lambda *_args, **_kwargs: {"running": True})
    assert sorted(backend.list_sessions()) == ["legacy-only", "new", "old"]
