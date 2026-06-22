"""Integration test for ut3server.

ENABLED (BYO): UT3 requires an operator-supplied server tree; OpenSpy creds are
optional for authenticated advertising.
"""

import os

import pytest

from conftest import require_command_for_runtime


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): copy an owned UT3 dedicated server tree into <install_dir>/ so Binaries/ut3 exists; set gsusername/gspassword if you want OpenSpy-authenticated advertising"
    ),
]
runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
module_name = "ut3server"


def test_ut3server_lifecycle(tmp_path):
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )
    del tmp_path
