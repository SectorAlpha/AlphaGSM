"""Real owned-asset lifecycle, deliberately pending operator-supplied MCC files."""

import os

import pytest

from conftest import require_integration_opt_in
from tests.smoke_tests.reclaimer_lifecycle import run_lifecycle

pytestmark = pytest.mark.integration


def test_projectreclaimer_lifecycle(tmp_path):
    require_integration_opt_in()
    source = os.environ.get("ALPHAGSM_RECLAIMER_ASSETS")
    if not source:
        pytest.skip("Pending real BYO validation: set ALPHAGSM_RECLAIMER_ASSETS to owned MCC files or a prepared export")
    report = run_lifecycle(tmp_path, source,
        backend=os.environ.get("ALPHAGSM_TEST_RUNTIME_BACKEND", "process"),
        image=os.environ.get("ALPHAGSM_BACKEND_DOCKER_IMAGE_WINE_PROTON"))
    assert report["protocol"] == "reclaimer_rcon"
