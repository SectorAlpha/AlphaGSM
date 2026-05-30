"""Integration test for mohaaserver.

ENABLED (BYO): MOHAA requires an operator-supplied 32-bit dedicated server tree.
"""

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): copy an owned MOHAA dedicated server tree into <install_dir>/ so mohaa_lnxded exists"
    ),
]


def test_mohaaserver_lifecycle(tmp_path):
    del tmp_path
