"""Integration test for mohaaserver.

Disabled: MOHAA requires user-provided 32-bit dedicated-server files.
"""

import pytest


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Disabled: requires user-provided 32-bit MOHAA dedicated-server files"),
]


def test_mohaaserver_lifecycle(tmp_path):
    del tmp_path