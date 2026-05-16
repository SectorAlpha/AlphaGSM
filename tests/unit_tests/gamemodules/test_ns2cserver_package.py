from pathlib import Path

import gamemodules.ns2cserver as ns2cserver


def test_ns2cserver_package_reexports_canonical_module_contract():
    assert Path(ns2cserver.__file__).name == "__init__.py"
    assert callable(ns2cserver.configure)
    assert callable(ns2cserver.install)
    assert callable(ns2cserver.get_start_command)
    assert ns2cserver.steam_app_id == 313900