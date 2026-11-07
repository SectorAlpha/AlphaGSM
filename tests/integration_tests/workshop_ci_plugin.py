"""Fail required anonymous Workshop CI files when any case skips."""

import os
from pathlib import Path

import pytest

from scripts.run_ci_workshop_tests import REPO_ROOT, WORKSHOP_TEST_FILES


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Retain normal reports except skips inside the explicit Workshop CI set."""
    del call
    outcome = yield
    report = outcome.get_result()
    if os.environ.get("ALPHAGSM_CI_WORKSHOP") != "1" or not report.skipped:
        return
    try:
        relative = Path(item.path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return
    if relative not in WORKSHOP_TEST_FILES:
        return
    report.sections.append(("Original Workshop skip", str(report.longrepr)))
    report.outcome = "failed"
    report.longrepr = (
        f"Required anonymous Workshop CI case skipped during {report.when}: {report.nodeid}. "
        "A skip cannot satisfy the required native Workshop lifecycle."
    )
    if hasattr(report, "wasxfail"):
        del report.wasxfail
