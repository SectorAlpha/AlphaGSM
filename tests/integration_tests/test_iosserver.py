"""Integration test for iosserver."""

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(
        reason=(
            "ENABLED (AUTH): authenticate Steam or SteamCMD with an account that can "
            "access IOSoccer Dedicated Server app 673990 branch iosoccer2025 or "
            "beta before setup; anonymous SteamCMD fails to set those sdk2013 "
            "branches and the public branch still crashes on Linux"
        )
    ),
]


def test_iosserver_lifecycle():
    """Covered by the ENABLED (AUTH) prerequisite path for now."""
