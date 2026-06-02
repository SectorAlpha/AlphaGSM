"""Integration test for dysserver."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason=(
            "ENABLED (AUTH): authenticate Steam or SteamCMD with an account that can "
            "access Dystopia Beta Dedicated Server app 17595 before setup; anonymous "
            "SteamCMD returns No subscription on the supported Previous/beta path"
        )
    ),
]


def test_dysserver_lifecycle():
    """Covered by the ENABLED (AUTH) prerequisite path for now."""
