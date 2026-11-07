"""Integration test: Run Minecraft Vanilla server in a Windows Docker container.

This test is a placeholder/skipped unless running on a Windows host with Docker Windows containers enabled.

Requirements:
- Windows 10/11/Server host
- Docker Desktop with Windows containers enabled
- Image: mcr.microsoft.com/windows/servercore:ltsc2022 (or similar)
- Java 17+ installed in the image
- Python 3.10+ installed in the image
- Minecraft Vanilla server JAR available (downloaded by test)

This test will:
- Build a Windows Docker image with Java and Python
- Copy the AlphaGSM repo into the container
- Run the subprocess backend to launch Minecraft
- Check that the server starts and responds

If not on Windows, this test is skipped.
"""

import sys
import pytest
from utils.platform_info import IS_WINDOWS

pytestmark = pytest.mark.backend_integration

@pytest.mark.skipif(not IS_WINDOWS, reason="Windows Docker containers required")
def test_minecraft_windows_container():
    pytest.skip("This test requires a Windows host with Docker Windows containers enabled.\n"
                "See backend_integration_tests/Dockerfile.windows and README.md for instructions.")
