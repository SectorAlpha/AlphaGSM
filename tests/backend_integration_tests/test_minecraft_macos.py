"""Integration test: Run Minecraft Vanilla server on macOS (subprocess backend).

This test is a placeholder/skipped unless running on macOS.

Requirements:
- macOS host
- Java 17+ installed
- Python 3.10+ installed

This test will:
- Download the Minecraft Vanilla server jar
- Run the subprocess backend to launch Minecraft
- Check that the server starts and responds

If not on macOS, this test is skipped.
"""

import sys
import os
import tempfile
import time
import urllib.request
import pytest
from utils.platform_info import IS_MACOS
from screen.subprocess_backend import SubprocessBackend, ProcessError

pytestmark = pytest.mark.backend_integration

SERVER_NAME = "bk-macos-mc"
START_TIMEOUT = 60
STOP_TIMEOUT = 20

@pytest.mark.skipif(not IS_MACOS, reason="macOS required")
def test_minecraft_macos_subprocess(tmp_path):
    # Download Minecraft server jar (latest release)
    mc_jar = tmp_path / "minecraft_server.jar"
    url = "https://launcher.mojang.com/v1/objects/fe3aa5b7e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5/server.jar"  # Example hash, update as needed
    urllib.request.urlretrieve(url, mc_jar)

    # Accept EULA
    (tmp_path / "eula.txt").write_text("eula=true\n")

    # Setup backend
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    session_tag = "MacMC#"
    keeplogs = 2
    backend = SubprocessBackend(session_tag, str(log_dir), keeplogs)

    # Start Minecraft server
    backend.start(SERVER_NAME, ["java", "-Xmx512M", "-Xms256M", "-jar", str(mc_jar), "nogui"], cwd=str(tmp_path))
    assert backend.is_running(SERVER_NAME)

    # Wait for server to start (look for "Done" in log)
    log_file = backend.logpath(SERVER_NAME)
    found = False
    for _ in range(START_TIMEOUT * 10):
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
                if "Done" in fh.read():
                    found = True
                    break
        time.sleep(0.1)
    assert found, "Minecraft server did not start in time"

    # Stop the server
    backend.send_input(SERVER_NAME, "stop\n")
    for _ in range(STOP_TIMEOUT * 10):
        if not backend.is_running(SERVER_NAME):
            break
        time.sleep(0.1)
    assert not backend.is_running(SERVER_NAME)

    # Check log for startup and shutdown
    with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
        log = fh.read()
    assert "Done" in log
    assert "Stopping the server" in log
