"""Full coverage tests for rs2server."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.rs2server', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.rs2server as mod
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
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["configfile"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Win64/VNGame.exe"
    server.data["Steam_AppID"] = 418480
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 418480
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 418480
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 418480
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
    server.data["exe_name"] = "Binaries/Win64/VNGame.exe"
    exe_path = tmp_path / "Binaries/Win64/VNGame.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "Binaries/Win64/VNGame.exe",
        "VNTE-CuChi?maxplayers=64",
        "-Port=27015",
        "-QueryPort=27015",
        "-ConfigSubDir=PCServer",
        "-log",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_uses_default_runtime_wrapper_on_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    observed = {}

    def fake_wrap_command(cmd, wineprefix=None, prefer_proton=False):
        observed["command"] = list(cmd)
        observed["wineprefix"] = wineprefix
        observed["prefer_proton"] = prefer_proton
        return ["proton", "run", *cmd]

    monkeypatch.setattr(mod.proton, "wrap_command", fake_wrap_command)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Win64/VNGame.exe"
    exe_path = tmp_path / "Binaries/Win64/VNGame.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27016

    cmd, cwd = mod.get_start_command(server)

    assert observed == {
        "command": [
            "Binaries/Win64/VNGame.exe",
            "VNTE-CuChi?maxplayers=64",
            "-Port=27015",
            "-QueryPort=27016",
            "-ConfigSubDir=PCServer",
            "-log",
        ],
        "wineprefix": None,
        "prefer_proton": False,
    }
    assert cmd[:2] == ["proton", "run"]
    assert cwd == server.data["dir"]


def test_query_and_info_address_use_queryport(monkeypatch):
    server = DummyServer("rs2")
    server.data["queryport"] = "27016"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.6")

    assert mod.get_query_address(server) == ("10.0.0.6", 27016, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.6", 27016, "a2s")


def test_setting_schema_exposes_rs2_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"
    assert mod.setting_schema["servername"].native_config_key == "ServerName"


def test_sync_server_config_updates_rs2_ini_server_name(tmp_path):
    server = DummyServer("rs2")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "configfile": "ROGame/Config/PCServer-ROGame.ini",
            "servername": "AlphaGSM RS2",
        }
    )
    ini_path = tmp_path / "ROGame/Config/PCServer-ROGame.ini"
    ini_path.parent.mkdir(parents=True)
    ini_path.write_text(
        "[/Script/Engine.GameReplicationInfo]\n"
        "ServerName=Old RS2\n\n"
        "[/Script/ROGame.ROGameInfoTerritories]\n"
        "RoundTimeLimit=600\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert ini_path.read_text(encoding="utf-8") == (
        "[/Script/Engine.GameReplicationInfo]\n"
        "ServerName=AlphaGSM RS2\n\n"
        "[/Script/ROGame.ROGameInfoTerritories]\n"
        "RoundTimeLimit=600\n"
    )


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
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


def test_checkvalue_configfile():
    server = DummyServer()
    result = mod.checkvalue(server, ("configfile",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "AlphaGSM RS2")
    assert result == "AlphaGSM RS2"


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

