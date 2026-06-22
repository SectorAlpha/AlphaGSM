"""Integration test for mohaaserver.

ENABLED (BYO): MOHAA requires an operator-supplied 32-bit dedicated server tree.
"""

import os

import pytest

from conftest import require_command_for_runtime, require_integration_opt_in

runtime_backend = os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process")
module_name = "mohaaserver"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): copy an owned MOHAA dedicated server tree into <install_dir>/ so mohaa_lnxded exists"
    ),
]


def test_mohaaserver_lifecycle(tmp_path):
    require_integration_opt_in()
    require_command_for_runtime(
        "docker", runtime_backend=runtime_backend, module_name=module_name
    )
    del tmp_path
