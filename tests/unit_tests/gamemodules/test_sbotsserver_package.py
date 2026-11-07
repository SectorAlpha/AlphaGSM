from pathlib import Path

import gamemodules.sbotsserver as sbotsserver


def test_sbotsserver_package_reexports_canonical_module_contract():
    assert Path(sbotsserver.__file__).name == "__init__.py"
    assert callable(sbotsserver.configure)
    assert callable(sbotsserver.install)
    assert callable(sbotsserver.get_start_command)
    assert sbotsserver.steam_app_id == 974130