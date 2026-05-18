"""Integration test for sof2server.

Disabled: SOF2 requires user-provided 32-bit dedicated-server files.
"""

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Disabled: requires user-provided 32-bit SOF2 dedicated-server files"),
]


def test_sof2server_lifecycle(tmp_path):
    del tmp_path