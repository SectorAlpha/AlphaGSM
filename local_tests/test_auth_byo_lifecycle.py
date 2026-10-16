"""Local AlphaGSM lifecycle tests for servers that need Steam auth or owned assets.

These tests download and start real servers. Select them with
scripts/run_local_auth_tests.sh integration --server NAME.
"""

import os
from pathlib import Path

import pytest

from catalog import selected_servers
from runner import lifecycle


def _rows():
    requested = os.environ.get("ALPHAGSM_LOCAL_SERVERS", "")
    suite = os.environ.get("ALPHAGSM_LOCAL_SUITE", "all")
    if not requested:
        return ()
    return selected_servers(suite, requested)


def pytest_configure(config):
    """Fail fast when an explicit server is not in either support list."""

    del config
    requested = os.environ.get("ALPHAGSM_LOCAL_SERVERS", "")
    if not requested or requested == "all":
        return
    known = {row["module"] for row in selected_servers("all", "all")}
    missing = sorted({
        item.strip() for item in requested.split(",") if item.strip() and item.strip() not in known
    })
    if missing:
        raise pytest.UsageError("Unknown AUTH or BYO server: " + ", ".join(missing))


@pytest.mark.parametrize("row", _rows(), ids=lambda row: row["suite"] + "-" + row["module"])
def test_selected_server_lifecycle(row):
    profile = os.environ.get("ALPHAGSM_LOCAL_AUTH_PROFILE", "").strip()
    assets = os.environ.get("ALPHAGSM_LOCAL_ASSETS", "").strip()
    state_dir = os.environ.get("ALPHAGSM_LOCAL_AUTH_STATE", "").strip()
    work_dir = os.environ.get("ALPHAGSM_LOCAL_WORK_DIR", "").strip()
    if not work_dir:
        raise AssertionError("ALPHAGSM_LOCAL_WORK_DIR is required and must stay outside git")
    if profile and not state_dir:
        raise AssertionError("Pass --state-dir for the existing Steam auth profile directory")
    if not profile and not assets:
        raise AssertionError("Pass --profile NAME or --assets PATH. Do not pass a password.")
    if state_dir:
        state_path = Path(state_dir).expanduser()
        if profile and not (state_path / "steam-auth" / profile).is_dir():
            raise AssertionError(
                "Steam auth profile %r is not present. Run alphagsm steam-auth login from a terminal."
                % profile
            )
    ready_timeout = int(os.environ.get("ALPHAGSM_LOCAL_READY_TIMEOUT", "180"))
    lifecycle(
        row["module"],
        profile=profile,
        assets=assets,
        state_dir=state_dir or str(Path(work_dir) / "state"),
        work_dir=work_dir,
        ready_timeout=ready_timeout,
    )
