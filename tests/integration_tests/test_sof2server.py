"""Integration test for sof2server.

ENABLED (BYO): SOF2 requires an operator-supplied 32-bit dedicated server tree.
"""

import os

import pytest

from conftest import default_runtime_backend, require_command_for_runtime


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): copy an owned SOF2 dedicated server tree into <install_dir>/ so sof2ded exists"
    ),
]
runtime_backend = os.environ.get(
    "ALPHAGSM_TEST_RUNTIME_BACKEND", default_runtime_backend()
)
module_name = "sof2server"


def test_sof2server_lifecycle(tmp_path):
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )
    del tmp_path
