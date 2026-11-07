"""Full coverage tests for vrserver."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.vrserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.vrserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=9876, dir=str(tmp_path))
    assert server.data['port'] == 9876


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 9876
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["9877", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "VRisingServer.exe"
    server.data["Steam_AppID"] = 1829350
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1829350
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1829350
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1829350
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
    server.data["exe_name"] = "VRisingServer.exe"
    (tmp_path / "VRisingServer.exe").write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    with patch.object(
        mod.proton,
        "wrap_command",
        side_effect=lambda command, **_kwargs: command,
    ):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "VRisingServer.exe",
        "-persistentDataPath",
        str(tmp_path / "save-data"),
        "-serverPort",
        "27015",
        "-queryPort",
        "27016",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_uses_relative_save_path_for_docker(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "VRisingServer.exe"
    server.data["runtime"] = "docker"
    (tmp_path / "VRisingServer.exe").write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    with patch.object(
        mod.proton,
        "wrap_command",
        side_effect=lambda command, **_kwargs: command,
    ):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "VRisingServer.exe",
        "-persistentDataPath",
        "./save-data",
        "-serverPort",
        "27015",
        "-queryPort",
        "27016",
    ]
    assert cwd == server.data["dir"]


def test_sync_server_config(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["servername"] = "AlphaGSM VR"
    server.data["port"] = 9876
    server.data["queryport"] = 9877
    server.data["maxplayers"] = 24

    mod.sync_server_config(server)

    config_path = tmp_path / "Settings" / "ServerHostSettings.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["Name"] == "AlphaGSM VR"
    assert payload["Port"] == 9876
    assert payload["QueryPort"] == 9877
    assert payload["MaxConnectedUsers"] == 24


def test_sync_server_config_no_dir_is_noop():
    server = DummyServer()
    server.data["servername"] = "AlphaGSM VR"
    server.data["port"] = 9876
    server.data["queryport"] = 9877
    server.data["maxplayers"] = 24
    mod.sync_server_config(server)


def test_get_query_and_info_address():
    server = DummyServer()
    server.data["queryport"] = 27016
    expected = ("127.0.0.1", 27016, "udp")
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected


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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "40")
    assert result == 40


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "AlphaGSM VR")
    assert result == "AlphaGSM VR"


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
