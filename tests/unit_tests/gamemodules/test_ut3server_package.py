from pathlib import Path

import gamemodules.ut3server as ut3server


def test_ut3server_package_reexports_canonical_module_contract():
    assert Path(ut3server.__file__).name == "__init__.py"
    assert callable(ut3server.configure)
    assert callable(ut3server.install)
    assert callable(ut3server.get_start_command)