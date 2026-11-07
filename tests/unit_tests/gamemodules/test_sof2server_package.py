from pathlib import Path

import gamemodules.sof2server as sof2server


def test_sof2server_package_reexports_canonical_module_contract():
    assert Path(sof2server.__file__).name == "__init__.py"
    assert callable(sof2server.configure)
    assert callable(sof2server.install)
    assert callable(sof2server.get_start_command)