from pathlib import Path

import gamemodules.tuserver as tuserver


def test_tuserver_package_reexports_canonical_module_contract():
    assert Path(tuserver.__file__).name == "__init__.py"
    assert callable(tuserver.configure)
    assert callable(tuserver.install)
    assert callable(tuserver.get_start_command)
    assert tuserver.steam_app_id == 439660