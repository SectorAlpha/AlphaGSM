"""Full coverage tests for craftopiaserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.craftopiaserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.craftopiaserver as mod
    from server import ServerError


class DummyData(dict):
    def save(self):
        pass
    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]
    def get(self, key, default=None):
        return super().get(key, default)


class DummyServer:
    def __init__(self, name="testserver"):
        self.name = name
        self.data = DummyData()
        self._stopped = False
        self._started = False
    def stop(self):
        self._stopped = True
    def start(self):
        self._started = True


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=8787, dir=str(tmp_path))
    assert server.data['port'] == 8787
    assert server.data['queryport'] == 8787
    assert server.data['backupfiles'] == ['DedicatedServerSave', 'ServerSetting.ini']


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8787
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["worldname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8788", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Craftopia.x86_64"
    server.data["Steam_AppID"] = 1670340
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 8787
    server.data["maxplayers"] = 8
    server.data["worldname"] = "AlphaGSM World"
    (tmp_path / "Craftopia.x86_64").write_text("")
    (tmp_path / "DefaultServerSetting.ini").write_text("[GameWorld]\nname=NoName\n\n[Host]\nport=6587\nmaxPlayerNumber=7\nusePassword=0\nserverPassword=00000000\nbindAddress=0.0.0.0\n\n[Save]\nsavePath=DedicatedServerSave/\n")
    mod.install(server)
    settings = (tmp_path / "ServerSetting.ini").read_text()
    assert "name=AlphaGSM World" in settings
    assert "port=8787" in settings
    assert "maxPlayerNumber=8" in settings
    assert f"savePath={tmp_path / 'DedicatedServerSave'}" in settings
    assert (tmp_path / "DedicatedServerSave").is_dir()


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1670340
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1670340
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1670340
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Craftopia.x86_64"
    (tmp_path / "Craftopia.x86_64").write_text("")
    (tmp_path / "DefaultServerSetting.ini").write_text("[GameWorld]\nname=NoName\n\n[Host]\nport=6587\nmaxPlayerNumber=7\nusePassword=0\nserverPassword=00000000\nbindAddress=0.0.0.0\n\n[Save]\nsavePath=DedicatedServerSave/\n")
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["worldname"] = "test"
    server.data["maxplayers"] = 8
    cmd, cwd = mod.get_start_command(server)
    assert cmd == ["./Craftopia.x86_64", "-batchmode", "-nographics"]
    assert cwd == str(tmp_path) + "/"
    settings = (tmp_path / "ServerSetting.ini").read_text()
    assert "name=test" in settings
    assert "port=27015" in settings


def test_get_query_address():
    server = DummyServer()
    server.data["port"] = 27015
    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "udp")


def test_get_info_address():
    server = DummyServer()
    server.data["port"] = 27015
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "udp")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["worldname"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.screen.send_to_server.assert_called()


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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "/test/value")
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

