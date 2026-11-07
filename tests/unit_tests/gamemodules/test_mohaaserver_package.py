from pathlib import Path

import gamemodules.mohaaserver as mohaaserver


def test_mohaaserver_package_reexports_canonical_module_contract():
    assert Path(mohaaserver.__file__).name == "__init__.py"
    assert callable(mohaaserver.configure)
    assert callable(mohaaserver.install)
    assert callable(mohaaserver.get_start_command)