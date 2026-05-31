"""Full coverage tests for rwserver."""

import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.rwserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.rwserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


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
    mod.configure(server, ask=False, port=4254, dir=str(tmp_path))
    assert server.data['port'] == 4254
    assert server.data["queryport"] == 4253


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 4254
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["javapath"] = "test"
    server.data["servername"] = "test"
    server.data["world"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["4255", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "RisingWorldServer.x64"
    server.data["Steam_AppID"] = 339010
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 339010
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 339010
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 339010
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
    server.data["exe_name"] = "RisingWorldServer.x64"
    (tmp_path / "RisingWorldServer.x64").write_text("")
    server.data["port"] = 27015
    server.data["world"] = "test"
    server.data["servername"] = "Alpha"
    cmd, cwd = mod.get_start_command(server)
    assert cmd[0:2] == ["sh", "-lc"]
    assert "RisingWorldServer.x64" in cmd[2]
    props = (tmp_path / "server.properties").read_text(encoding="utf-8")
    assert "Server_Port=27015" in props
    assert "World_Name=test" in props
    assert "Server_Name=Alpha" in props


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["world"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_query_address_uses_derived_query_port(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 4255
    address = mod.get_query_address(server)
    assert address == ("127.0.0.1", 4254, "tcp")


def test_sync_server_config_writes_native_keys(tmp_path):
    server = DummyServer("rw")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 4255,
            "servername": "AlphaGSM RW",
            "world": "myworld",
        }
    )
    mod.sync_server_config(server)
    props = (tmp_path / "server.properties").read_text(encoding="utf-8")
    assert "Server_Port=4255" in props
    assert "Server_Name=AlphaGSM RW" in props
    assert "World_Name=myworld" in props


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


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


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_world():
    server = DummyServer()
    result = mod.checkvalue(server, ("world",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_javapath():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("javapath",), "/test/value")


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
