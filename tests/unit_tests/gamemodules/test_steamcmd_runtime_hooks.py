import types

import importlib


class FakeServer:
    def __init__(self):
        self.name = "test"
        self.data = {
            "dir": "/tmp",
            "port": 27015,
            "exe_name": "server",
            "version": "latest",
        }


def assert_runtime_family(module_name, expected_family="steamcmd-linux"):
    mod = importlib.import_module(module_name)
    hook = getattr(mod, "get_runtime_requirements", None)
    assert callable(hook), f"{module_name} missing get_runtime_requirements"
    req = hook(FakeServer())
    # builders return a mapping with 'family' or 'runtime_family'
    family = req.get("family") or req.get("runtime_family")
    assert family == expected_family, f"{module_name} family={family} expected={expected_family}"


def test_counterstrike2_runtime():
    assert_runtime_family("gamemodules.counterstrike2", "steamcmd-linux")


def test_gmodserver_runtime():
    assert_runtime_family("gamemodules.gmodserver", "steamcmd-linux")


def test_teamfortress2_runtime():
    assert_runtime_family("gamemodules.teamfortress2", "steamcmd-linux")


def test_tf2cserver_runtime():
    assert_runtime_family("gamemodules.tf2cserver", "steamcmd-linux")


def test_tuserver_runtime():
    assert_runtime_family("gamemodules.tuserver", "steamcmd-linux")
