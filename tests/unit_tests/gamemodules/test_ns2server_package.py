from pathlib import Path

import gamemodules.ns2server as ns2server


def test_ns2server_package_reexports_canonical_module_contract():
    assert Path(ns2server.__file__).name == "__init__.py"
    assert callable(ns2server.configure)
    assert callable(ns2server.install)
    assert callable(ns2server.get_start_command)
    assert ns2server.steam_app_id == 4940