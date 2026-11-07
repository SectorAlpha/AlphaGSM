from pathlib import Path

import gamemodules.wetserver as wetserver


def test_wetserver_package_reexports_canonical_module_contract():
    assert Path(wetserver.__file__).name == "__init__.py"
    assert callable(wetserver.configure)
    assert callable(wetserver.install)
    assert callable(wetserver.get_start_command)
    assert wetserver.WET_DOWNLOAD_URL.endswith("et260b.x86_full.zip")