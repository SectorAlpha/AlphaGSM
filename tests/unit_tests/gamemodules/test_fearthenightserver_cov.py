"""Full coverage tests for fearthenightserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.fearthenightserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.fearthenightserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data["queryport"] == "27015"
    assert server.data["maxplayers"] == "40"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Moonlight/Binaries/Win64/MoonlightServer.exe"
    server.data["Steam_AppID"] = 764940
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 764940
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 764940
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 764940
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
    server.data["exe_name"] = "Moonlight/Binaries/Win64/MoonlightServer.exe"
    exe_path = tmp_path / "Moonlight/Binaries/Win64/MoonlightServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["startmap"] = "test"
    server.data["port"] = 7778
    server.data["queryport"] = 27017
    server.data["maxplayers"] = 12
    server.data["servername"] = "Alpha Test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cmd[1] == "test?listen?Port=7778?QueryPort=27017?SessionName=Alpha Test?MaxPlayers=12"
    assert cwd == server.data["dir"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop(monkeypatch):
    server = DummyServer()
    send_calls = []
    monkeypatch.setattr(mod.runtime_module, "send_to_server", lambda current, text: send_calls.append((current, text)))
    mod.do_stop(server, 0)
    assert send_calls == [(server, "\003")]


def test_get_query_address_linux(monkeypatch):
    server = DummyServer()
    server.data["port"] = 58055
    server.data["queryport"] = 27019
    mod.runtime_module.resolve_query_host.return_value = "127.0.0.1"
    monkeypatch.setattr(mod, "IS_LINUX", True)
    assert mod.get_query_address(server) == ("127.0.0.1", 58055, "udp")
    assert mod.get_info_address(server) == ("127.0.0.1", 58055, "udp")


def test_get_query_address_non_linux(monkeypatch):
    server = DummyServer()
    server.data["queryport"] = 27019
    mod.runtime_module.resolve_query_host.return_value = "127.0.0.1"
    monkeypatch.setattr(mod, "IS_LINUX", False)
    assert mod.get_query_address(server) == ("127.0.0.1", 27019, "a2s")


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
    result = mod.checkvalue(server, ("queryport",), "27019")
    assert result == 27019


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "24")
    assert result == 24


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "Alpha Test")
    assert result == "Alpha Test"


def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
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


def test_sync_server_config_writes_engine_and_game_settings(tmp_path):
    server = DummyServer("fear")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 58055,
            "queryport": 58056,
            "maxplayers": 18,
            "servername": "Fear Alpha",
        }
    )
    settings_dir = tmp_path / "Moonlight" / "Saved" / "Config" / "WindowsServer"
    settings_dir.mkdir(parents=True)
    (settings_dir / "GameUserSettings.ini").write_text("[ServerSettings]\nRCONPort=27020\n", encoding="utf-8")

    mod.sync_server_config(server)

    engine_text = (settings_dir / "Engine.ini").read_text(encoding="utf-8")
    assert "Port = 58055" in engine_text
    assert "PeerPort = 58056" in engine_text
    assert "GameServerQueryPort = 58056" in engine_text

    game_user_settings_text = (settings_dir / "GameUserSettings.ini").read_text(encoding="utf-8")
    assert "SessionName = Fear Alpha" in game_user_settings_text
    assert "MaxPlayers = 18" in game_user_settings_text
