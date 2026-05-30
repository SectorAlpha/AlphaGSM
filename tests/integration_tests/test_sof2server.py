"""Integration test for sof2server.

ENABLED (BYO): SOF2 requires an operator-supplied 32-bit dedicated server tree.
"""

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): copy an owned SOF2 dedicated server tree into <install_dir>/ so sof2ded exists"
    ),
]


def test_sof2server_lifecycle(tmp_path):
    del tmp_path
