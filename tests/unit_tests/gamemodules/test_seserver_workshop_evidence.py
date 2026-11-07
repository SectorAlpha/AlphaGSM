"""Space Engineers Workshop proof must establish execution of the mod script."""

import pytest

from tests.smoke_tests.seserver_workshop import assert_workshop_executed


def test_mod_script_startup_and_ready_prove_native_execution():
    assert_workshop_executed("Thread: 1 -> MES Spawner / Startup: Active Debug Not Found\nGame ready")


@pytest.mark.parametrize("text", [
    "Modular Encounters Systems 1521905890\nGame ready",
    "Downloading 1521905890.sbm\nGame ready",
    "MES Spawner / Startup: Active Debug Not Found",
    "MES Spawner / Startup: Active Debug Not Found\nMOD_CRITICAL_ERROR: Modular Encounters Systems\nGame ready",
])
def test_config_download_or_failed_script_cannot_satisfy_execution(text):
    with pytest.raises(AssertionError):
        assert_workshop_executed(text)
