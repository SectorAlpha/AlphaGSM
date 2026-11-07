from pathlib import Path

import gamemodules.tf2cserver as tf2c


def test_tf2cserver_package_reexports_canonical_module_contract():
    assert Path(tf2c.__file__).name == "__init__.py"
    assert callable(tf2c.configure)
    assert callable(tf2c.install)
    assert callable(tf2c.get_start_command)
    assert tf2c.steam_app_id == 3557020
    assert tf2c.base_steam_app_id == 232250