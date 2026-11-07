"""Full coverage tests for miscreatedserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.miscreatedserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.miscreatedserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=64090, dir=str(tmp_path))
    assert server.data['port'] == 64090


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 64090
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["gameserverid"] = "test"
    server.data["maxplayers"] = 27015
    server.data["servername"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["64091", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Bin64_dedicated/MiscreatedServer.exe"
    server.data["Steam_AppID"] = 302200
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 302200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 302200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 302200
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Bin64_dedicated/MiscreatedServer.exe"
    exe_path = tmp_path / "Bin64_dedicated/MiscreatedServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["gameserverid"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["servername"] = "test"
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_miscreated_runtime_metadata_enables_xvfb_for_docker(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Bin64_dedicated/MiscreatedServer.exe",
            "gameserverid": "100",
            "maxplayers": 50,
            "port": 64090,
            "servername": "AlphaGSM miscreated",
            "startmap": "islands",
        }
    )
    exe_path = tmp_path / "Bin64_dedicated" / "MiscreatedServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert spec["env"]["ALPHAGSM_XVFB"] == "1"
    assert spec["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"


def test_query_addresses_use_tcp_on_linux(monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    server = DummyServer()
    server.data.update({"port": 64090})

    assert mod.get_query_address(server) == ("127.0.0.1", 64090, "tcp")
    assert mod.get_info_address(server) == ("127.0.0.1", 64090, "tcp")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["gameserverid"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["servername"] = "test"
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_once_with(server, "\003")


def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)


def test_message():
    server = DummyServer()
    mod.message(server, "hello")


def test_backup():
    server = DummyServer()
    server.data["dir"] = "/tmp/test/"
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.backup(server)


def test_checkvalue_empty_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ())


def test_checkvalue_unsupported_key():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("totally_invalid_key_xyz",), "val")


def test_checkvalue_no_value():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("port",))


def test_checkvalue_port():
    server = DummyServer()
    result = mod.checkvalue(server, ("port",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_gameserverid():
    server = DummyServer()
    result = mod.checkvalue(server, ("gameserverid",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
