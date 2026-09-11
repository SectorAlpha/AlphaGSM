from pathlib import Path

import gamemodules.onsetserver as onsetserver


def test_onsetserver_package_reexports_canonical_module_contract():
    assert Path(onsetserver.__file__).name == "__init__.py"
    assert callable(onsetserver.configure)
    assert callable(onsetserver.install)
    assert callable(onsetserver.get_start_command)
    assert onsetserver.steam_app_id == 1204170