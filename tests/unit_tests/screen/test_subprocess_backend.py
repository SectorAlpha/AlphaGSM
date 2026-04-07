"""Tests for SubprocessBackend."""

import os
import signal
import subprocess as sp

import pytest

from screen.subprocess_backend import SubprocessBackend, _processes
from screen.backend import ProcessError


def _make_backend(tmp_path):
    logdir = tmp_path / "logs"
    logdir.mkdir(exist_ok=True)
    return SubprocessBackend("Alpha#", str(logdir), 5)


@pytest.fixture(autouse=True)
def _clear_process_registry():
    """Ensure the module-level registry is empty between tests."""
    _processes.clear()
    yield
    # Kill any leaked processes.
    for name, (proc, logfh) in list(_processes.items()):
        try:
            proc.kill()
        except OSError:
            pass
        logfh.close()
    _processes.clear()


def test_backend_name():
    assert SubprocessBackend("X#", "/tmp", 5).backend_name == "subprocess"


def test_start_creates_pidfile_and_log(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    logdir = tmp_path / "logs"
    assert (logdir / "Alpha#srv1.pid").exists()
    assert (logdir / "Alpha#srv1.log").exists()
    pid = int((logdir / "Alpha#srv1.pid").read_text().strip())
    assert pid > 0
    backend.kill("srv1")


def test_start_raises_when_already_running(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    with pytest.raises(ProcessError, match="already running"):
        backend.start("srv1", ["sleep", "60"])
    backend.kill("srv1")


def test_start_raises_on_bad_command(tmp_path):
    backend = _make_backend(tmp_path)
    with pytest.raises(ProcessError, match="Can't start process"):
        backend.start("srv1", ["/nonexistent_binary_XYZ_1234"])


def test_is_running_true_while_process_alive(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    assert backend.is_running("srv1") is True
    backend.kill("srv1")


def test_is_running_false_after_process_exits(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["true"])
    # Wait for the short-lived process to exit.
    _processes["srv1"][0].wait(timeout=5)
    assert backend.is_running("srv1") is False


def test_is_running_false_for_unknown_name(tmp_path):
    backend = _make_backend(tmp_path)
    assert backend.is_running("unknown") is False


def test_kill_terminates_process(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    backend.kill("srv1")
    assert backend.is_running("srv1") is False
    assert not (tmp_path / "logs" / "Alpha#srv1.pid").exists()


def test_kill_via_pidfile(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    pid = _processes["srv1"][0].pid
    # Remove from in-memory registry to simulate a new invocation.
    _processes["srv1"][1].close()
    del _processes["srv1"]
    backend.kill("srv1")
    # PID should be gone.
    try:
        os.kill(pid, 0)
        alive = True
    except ProcessLookupError:
        alive = False
    assert not alive or not (tmp_path / "logs" / "Alpha#srv1.pid").exists()


def test_kill_raises_for_unknown_session(tmp_path):
    backend = _make_backend(tmp_path)
    with pytest.raises(ProcessError, match="No running session"):
        backend.kill("nope")


def test_send_raw_raises(tmp_path):
    backend = _make_backend(tmp_path)
    with pytest.raises(ProcessError, match="send_raw is not supported"):
        backend.send_raw("srv1", ["anything"])


def test_send_input_writes_to_stdin(tmp_path):
    backend = _make_backend(tmp_path)
    # Start cat so it reads stdin and writes to stdout (our log file).
    backend.start("srv1", ["cat"])
    backend.send_input("srv1", "hello\n")
    # Close stdin so cat flushes and exits.
    proc = _processes["srv1"][0]
    proc.stdin.close()
    proc.wait(timeout=5)
    _processes["srv1"][1].close()
    del _processes["srv1"]
    backend._cleanup_pidfile("srv1")
    log = (tmp_path / "logs" / "Alpha#srv1.log").read_text()
    assert "hello" in log


def test_send_input_ctrl_c_sends_sigint(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    pid = _processes["srv1"][0].pid
    backend.send_input("srv1", "\003")
    # Process should receive SIGINT and likely terminate.
    _processes["srv1"][0].wait(timeout=5)
    assert _processes.get("srv1") is not None  # still in registry until is_running cleans up


def test_send_input_raises_for_unknown_session(tmp_path):
    backend = _make_backend(tmp_path)
    with pytest.raises(ProcessError, match="Cannot send input"):
        backend.send_input("unknown", "hello")


def test_list_sessions_finds_running(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["sleep", "60"])
    backend.start("srv2", ["sleep", "60"])
    names = list(backend.list_sessions())
    assert sorted(names) == ["srv1", "srv2"]
    backend.kill("srv1")
    backend.kill("srv2")


def test_list_sessions_excludes_dead(tmp_path):
    backend = _make_backend(tmp_path)
    backend.start("srv1", ["true"])
    _processes["srv1"][0].wait(timeout=5)
    names = list(backend.list_sessions())
    assert "srv1" not in names


def test_connect_raises_when_no_log(tmp_path):
    backend = _make_backend(tmp_path)
    with pytest.raises(ProcessError, match="No log file"):
        backend.connect("srv1")
