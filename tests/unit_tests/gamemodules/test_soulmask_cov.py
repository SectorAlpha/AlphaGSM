"""Full coverage tests for soulmask."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.soulmask', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.soulmask as mod
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
    mod.configure(server, ask=False, port=8777, dir=str(tmp_path))
    assert server.data['port'] == 8777


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["adminpassword"] = "test"
    server.data["backupinterval"] = "test"
    server.data["bindaddress"] = "test"
    server.data["echoport"] = "test"
    server.data["level"] = "test"
    server.data["maxplayers"] = 27015
    server.data["mods"] = "test"
    server.data["queryport"] = 27015
    server.data["savinginterval"] = "test"
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "WSServer.sh"
    server.data["Steam_AppID"] = 3017300
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3017300
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3017300
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3017300
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
    server.data["exe_name"] = "WSServer.sh"
    (tmp_path / "WSServer.sh").write_text("")
    server.data["adminpassword"] = "test"
    server.data["backupinterval"] = "test"
    server.data["bindaddress"] = "test"
    server.data["echoport"] = "test"
    server.data["level"] = "test"
    server.data["maxplayers"] = 27015
    server.data["mods"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["savinginterval"] = "test"
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./WSServer.sh",
        "test",
        "-server",
        "-log",
        "-forcepassthrough",
        "-UTF8Output",
        "-SteamServerName=test",
        "-MaxPlayers=27015",
        "-PSW=test",
        "-adminpsw=test",
        "-MULTIHOME=test",
        "-Port=27015",
        "-QueryPort=27015",
        "-EchoPort=test",
        "-saving=test",
        "-backup=test",
        '-mod="test"',
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_launch_formats():
    assert mod.setting_schema["level"].launch_arg_format == "{value}"
    assert mod.setting_schema["servername"].launch_arg_format == "-SteamServerName={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "-MaxPlayers={value}"
    assert mod.setting_schema["serverpassword"].launch_arg_format == "-PSW={value}"
    assert mod.setting_schema["adminpassword"].launch_arg_format == "-adminpsw={value}"
    assert mod.setting_schema["bindaddress"].launch_arg_format == "-MULTIHOME={value}"
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"
    assert mod.setting_schema["echoport"].launch_arg_format == "-EchoPort={value}"
    assert mod.setting_schema["savinginterval"].launch_arg_format == "-saving={value}"
    assert mod.setting_schema["backupinterval"].launch_arg_format == "-backup={value}"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["adminpassword"] = "test"
    server.data["backupinterval"] = "test"
    server.data["bindaddress"] = "test"
    server.data["echoport"] = "test"
    server.data["level"] = "test"
    server.data["maxplayers"] = 27015
    server.data["mods"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["savinginterval"] = "test"
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
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


def test_checkvalue_echoport():
    server = DummyServer()
    result = mod.checkvalue(server, ("echoport",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_backupinterval():
    server = DummyServer()
    result = mod.checkvalue(server, ("backupinterval",), "12345")
    assert result == 12345


def test_checkvalue_savinginterval():
    server = DummyServer()
    result = mod.checkvalue(server, ("savinginterval",), "12345")
    assert result == 12345


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_level():
    server = DummyServer()
    result = mod.checkvalue(server, ("level",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_bindaddress():
    server = DummyServer()
    result = mod.checkvalue(server, ("bindaddress",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_mods():
    server = DummyServer()
    result = mod.checkvalue(server, ("mods",), "/test/value")
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

