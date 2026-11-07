from pathlib import Path

import gamemodules.hcuserver as hcuserver


def test_hcuserver_package_reexports_canonical_module_contract():
    assert Path(hcuserver.__file__).name == "__init__.py"
    assert callable(hcuserver.configure)
    assert callable(hcuserver.install)
    assert callable(hcuserver.get_start_command)
    assert hcuserver.steam_app_id == 1045940