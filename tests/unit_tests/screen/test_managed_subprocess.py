"""Real independent-invocation checks for persistent process control."""

import os
from pathlib import Path
import subprocess
import sys
import time

from screen.managed_subprocess import ManagedSubprocessBackend


def test_console_survives_starting_cli_exit(tmp_path):
    """A later invocation can send stdin and shut down without losing saves."""
    logdir = tmp_path / "logs with spaces"
    server = tmp_path / "server.py"
    server.write_text(
        "import sys\n"
        "for line in sys.stdin:\n"
        " print(line.strip(), flush=True)\n"
        " if line.strip() == 'stop': break\n"
        "print('saved', flush=True)\n", encoding="utf-8",
    )
    script = (
        "from screen.managed_subprocess import ManagedSubprocessBackend\n"
        "import sys\n"
        "ManagedSubprocessBackend('Test#', sys.argv[1], 2).start("
        "'one', [sys.executable, '-u', sys.argv[2]])\n"
    )
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[3] / "src"))
    subprocess.run([sys.executable, "-c", script, str(logdir), str(server)],
                   env=env, check=True, timeout=30)
    backend = ManagedSubprocessBackend("Test#", str(logdir), 2)
    try:
        assert backend.is_running("one")
        backend.send_input("one", "hello\n")
        backend.send_input("one", "stop\n")
        deadline = time.monotonic() + 10
        while backend.is_running("one") and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not backend.is_running("one")
        assert "hello\nstop\nsaved" in Path(backend.logpath("one")).read_text()
    finally:
        if backend.is_running("one"):
            backend.kill("one")


def test_missing_executable_fails_start(tmp_path):
    import pytest
    from screen.backend import ProcessError

    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    with pytest.raises(ProcessError, match="start"):
        backend.start("missing", [str(tmp_path / "absent")])
    assert not backend.is_running("missing")


def test_non_ascii_credential_does_not_stop_supervisor(tmp_path):
    import json
    import socket
    from screen.supervisor import read_message

    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    backend.start("auth", [sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        endpoint = json.loads((backend._session_path("auth") / "endpoint.json").read_text())
        with socket.create_connection(("127.0.0.1", endpoint["port"]), timeout=3) as connection:
            connection.sendall(json.dumps({"token": "wrong-☃", "action": "kill"}).encode() + b"\n")
            response = read_message(connection)
        assert not response["ok"]
        assert backend.is_running("auth")
    finally:
        if backend.is_running("auth"):
            backend.kill("auth")


def test_blocked_stdin_does_not_block_ping_or_kill(tmp_path):
    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    backend.start("blocked", [sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        for _ in range(3):
            backend.send_input("blocked", "x" * 60000)
        assert backend.is_running("blocked")
        backend.kill("blocked")
        assert not backend.is_running("blocked")
    finally:
        # Last-resort cleanup also works against the original blocked implementation.
        import json
        import signal
        endpoint = backend._session_path("blocked") / "endpoint.json"
        if endpoint.exists():
            pid = json.loads(endpoint.read_text())["pid"]
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def test_dead_endpoint_can_be_replaced_when_worker_and_game_are_gone(tmp_path, monkeypatch):
    import json

    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    session = backend._session_path("stale")
    session.mkdir()
    (session / "endpoint.json").write_text(json.dumps({"port": 1, "token": "unused", "pid": 999999999}))
    monkeypatch.setattr(backend, "_is_pid_alive", lambda _pid: False)
    backend.start("stale", [sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        assert backend.is_running("stale")
    finally:
        if backend.is_running("stale"):
            backend.kill("stale")


def test_failed_helper_launch_allows_immediate_retry(tmp_path, monkeypatch):
    import pytest
    import screen.managed_subprocess as module
    from screen.backend import ProcessError

    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    with monkeypatch.context() as patch:
        def fail_launch(*_args, **_kwargs):
            raise OSError("launch denied")
        patch.setattr(module.subprocess, "Popen", fail_launch)
        with pytest.raises(ProcessError, match="launch denied"):
            backend.start("retry", [sys.executable, "-c", "import time; time.sleep(60)"])
    backend.start("retry", [sys.executable, "-c", "import time; time.sleep(60)"])
    backend.kill("retry")


@__import__("pytest").mark.skipif(sys.platform != "win32", reason="requires native Windows Job Objects")
def test_windows_job_cleans_descendant_after_parent_exits(tmp_path):
    from core.binary_update import _wait_for_parent_exit

    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    server = tmp_path / "parent.py"
    server.write_text(
        "import subprocess, sys\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "print(child.pid, flush=True)\n"
        "for line in sys.stdin:\n"
        " if line.strip() == 'stop': break\n", encoding="utf-8",
    )
    backend.start("family", [sys.executable, "-u", str(server)])
    try:
        log = Path(backend.logpath("family"))
        deadline = time.monotonic() + 10
        child_pid = None
        while time.monotonic() < deadline:
            lines = log.read_text().splitlines()
            if lines:
                child_pid = int(lines[0])
                break
            time.sleep(0.05)
        assert child_pid is not None
        backend.send_input("family", "stop\n")
        _wait_for_parent_exit(child_pid, 10)
        assert not backend.is_running("family")
    finally:
        if backend.is_running("family"):
            backend.kill("family")


def test_windows_supervisor_gets_hidden_independent_console(monkeypatch):
    from types import SimpleNamespace
    import screen.managed_subprocess as module

    startup = SimpleNamespace(dwFlags=0, wShowWindow=None)
    fake_subprocess = SimpleNamespace(STARTUPINFO=lambda: startup,
                                     STARTF_USESHOWWINDOW=1, SW_HIDE=0,
                                     CREATE_NEW_CONSOLE=16, CREATE_NEW_PROCESS_GROUP=512)
    monkeypatch.setattr(module, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(module, "subprocess", fake_subprocess)
    options = module.helper_launch_options()
    assert options["creationflags"] == 16 | 512
    assert options["startupinfo"] is startup
    assert startup.dwFlags & 1
    assert startup.wShowWindow == 0


@__import__("pytest").mark.skipif(sys.platform == "win32", reason="Windows supervisor crashes use Job Object cleanup")
def test_supervisor_termination_stops_owned_process(tmp_path):
    import json
    import signal

    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    backend.start("terminated", [sys.executable, "-c", "import time; time.sleep(60)"])
    session = backend._session_path("terminated")
    endpoint = json.loads((session / "endpoint.json").read_text())
    try:
        os.kill(endpoint["supervisor_pid"], signal.SIGTERM)
        deadline = time.monotonic() + 10
        while not (session / "stopped.json").exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert (session / "stopped.json").exists()
        assert not backend._is_pid_alive(endpoint["pid"])
    finally:
        if backend.is_running("terminated"):
            backend.kill("terminated")


@__import__("pytest").mark.skipif(sys.platform != "win32", reason="requires native Windows console events")
def test_windows_console_break_reaches_server(tmp_path):
    backend = ManagedSubprocessBackend("Test#", str(tmp_path), 2)
    script = (
        "import signal, sys, time\n"
        "def stop(*args):\n"
        " print('graceful break', flush=True)\n"
        " sys.exit(0)\n"
        "signal.signal(signal.SIGBREAK, stop)\n"
        "print('ready', flush=True)\n"
        "while True: time.sleep(0.1)\n"
    )
    backend.start("console", [sys.executable, "-u", "-c", script])
    try:
        log = Path(backend.logpath("console"))
        deadline = time.monotonic() + 10
        while "ready" not in log.read_text().splitlines() and time.monotonic() < deadline:
            time.sleep(0.05)
        contents = log.read_text()
        assert "ready" in contents.splitlines(), contents
        backend.send_input("console", "\003")
        deadline = time.monotonic() + 10
        while backend.is_running("console") and time.monotonic() < deadline:
            time.sleep(0.05)
        stopped = backend._session_path("console") / "stopped.json"
        while not stopped.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        contents = log.read_text()
        assert not backend.is_running("console"), contents
        assert stopped.exists(), contents
        assert "graceful break" in contents.splitlines(), contents
        assert "Traceback" not in contents, contents
    finally:
        if backend.is_running("console"):
            backend.kill("console")
