"""Keep Steam-auth and BYO asset tests off CI and off accidental pytest runs."""

import os
from pathlib import Path

import pytest


def _ci_requested():
    return os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("CI") in {"1", "true"}


if _ci_requested():
    raise pytest.UsageError(
        "local_tests are local-only. CI must not collect or run Steam auth or BYO asset tests."
    )

if os.environ.get("ALPHAGSM_RUN_LOCAL_TESTS") != "1":
    raise pytest.UsageError(
        "Use scripts/run_local_auth_tests.sh. It sets ALPHAGSM_RUN_LOCAL_TESTS=1."
    )

os.environ.setdefault(
    "ALPHAGSM_CONFIG_LOCATION",
    str(Path(__file__).resolve().parents[1] / "tests" / "alphagsm-test.conf"),
)
