"""Integration test for the Python subprocess backend (cross-platform)."""

import os
import sys
import tempfile
import time
import shutil
import pytest

from utils.platform_info import IS_WINDOWS
from screen.subprocess_backend import SubprocessBackend, ProcessError

pytestmark = pytest.mark.backend_integration

SERVER_NAME = "bk-subproc-integration"
START_TIMEOUT = 30
STOP_TIMEOUT = 10


def test_subprocess_backend_lifecycle(tmp_path):
    """Full create → start → send input → stop cycle for subprocess backend."""
    # Setup log dir
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    session_tag = "PySub#"
    keeplogs = 2
    backend = SubprocessBackend(session_tag, str(log_dir), keeplogs)

    # Write a simple Python server script that echoes lines and exits on 'quit'
    server_script = tmp_path / "echo_server.py"
    server_script.write_text(
        """
import sys\nfor line in sys.stdin:\n    print('ECHO:', line.strip())\n    sys.stdout.flush()\n    if line.strip() == 'quit':\n        break\n"""
    )

    # Start the server
    backend.start(SERVER_NAME, [sys.executable, str(server_script)])
    assert backend.is_running(SERVER_NAME)

    # Send input and check log
    backend.send_input(SERVER_NAME, "hello world\n")
    backend.send_input(SERVER_NAME, "quit\n")

    # Wait for process to exit
    for _ in range(STOP_TIMEOUT * 10):
        if not backend.is_running(SERVER_NAME):
            break
        time.sleep(0.1)
    assert not backend.is_running(SERVER_NAME)

    # Check log file for expected output
    log_file = backend.logpath(SERVER_NAME)
    with open(log_file, "r", encoding="utf-8") as fh:
        log = fh.read()
    assert "ECHO: hello world" in log
    assert "ECHO: quit" in log
