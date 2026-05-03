from pathlib import Path

import gamemodules.teamfortress2 as tf2


def test_teamfortress2_package_reexports_canonical_module_contract():
    assert Path(tf2.__file__).name == "__init__.py"
    assert callable(tf2.configure)
    assert callable(tf2.install)
    assert callable(tf2.get_start_command)
    assert tf2.steam_app_id == 232250
