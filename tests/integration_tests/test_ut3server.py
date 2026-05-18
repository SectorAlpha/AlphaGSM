"""Integration test for ut3server.

Disabled: UT3 requires user-provided server files and OpenSpy credentials.
"""

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Disabled: requires user-provided UT3 server files and OpenSpy credentials (bring-your-own)"),
]


def test_ut3server_lifecycle(tmp_path):
    del tmp_path