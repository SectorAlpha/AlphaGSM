"""Integration test for ut3server.

ENABLED (BYO): UT3 requires an operator-supplied server tree; OpenSpy creds are
optional for authenticated advertising.
"""

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason="ENABLED (BYO): copy an owned UT3 dedicated server tree into <install_dir>/ so Binaries/ut3 exists; set gsusername/gspassword if you want OpenSpy-authenticated advertising"
    ),
]


def test_ut3server_lifecycle(tmp_path):
    del tmp_path
