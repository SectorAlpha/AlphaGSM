"""Full coverage tests for conanexiles."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.modules.pop("gamemodules.conanexiles", None)
with patch.dict(
    "sys.modules",
    {
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.conanexiles as mod
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
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data["port"] == 7777
    assert server.data["exe_name"] == "ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 40
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / "custom")])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception("already stopped"))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_sync_server_config(tmp_path):
    server = DummyServer("conan")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["maxplayers"] = 24
    server.data["servername"] = "AlphaGSM Conan"

    mod.sync_server_config(server)

    engine_text = (tmp_path / "ConanSandbox" / "Saved" / "Config" / "WindowsServer" / "Engine.ini").read_text(encoding="utf-8")
    game_text = (tmp_path / "ConanSandbox" / "Saved" / "Config" / "WindowsServer" / "Game.ini").read_text(encoding="utf-8")
    server_settings_text = (tmp_path / "ConanSandbox" / "Saved" / "Config" / "WindowsServer" / "ServerSettings.ini").read_text(encoding="utf-8")

    assert "Port=7777" in engine_text
    assert "GameServerQueryPort=27015" in engine_text
    assert "ServerName=AlphaGSM Conan" in engine_text
    assert "MaxPlayers=24" in game_text
    assert "[ServerSettings]" in server_settings_text


def test_sync_server_config_no_dir_is_noop():
    server = DummyServer()
    server.data["servername"] = "AlphaGSM Conan"
    mod.sync_server_config(server)


def test_get_start_command_prefers_shipping_executable(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "ConanSandbox" / "Binaries" / "Win64" / "ConanSandboxServer-Win64-Shipping.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = "ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 16
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    with patch.object(mod, "IS_LINUX", False):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe",
        "ConanSandbox",
        "-log",
        "-Port=7777",
        "-QueryPort=27015",
        "-MaxPlayers=16",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_accepts_wrapper_fallback(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "ConanSandboxServer.exe"
    exe.write_text("")
    server.data["exe_name"] = "ConanSandboxServer.exe"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 16
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    with patch.object(mod, "IS_LINUX", False):
        cmd, _cwd = mod.get_start_command(server)
    assert cmd[0] == "ConanSandboxServer.exe"


def test_setting_schema_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "-MaxPlayers={value}"


def test_get_query_and_info_address():
    server = DummyServer()
    server.data["queryport"] = 27015
    expected = ("127.0.0.1", 27015, "a2s")
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 16
    server.data["port"] = 7777
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
    server.data["backup"] = {
        "profiles": {"default": {"targets": ["saves"]}},
        "schedule": [("default", 0, "days")],
    }
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
    assert mod.checkvalue(server, ("port",), "12345") == 12345


def test_checkvalue_queryport():
    server = DummyServer()
    assert mod.checkvalue(server, ("queryport",), "27015") == 27015


def test_checkvalue_maxplayers():
    server = DummyServer()
    assert mod.checkvalue(server, ("maxplayers",), "70") == 70


def test_checkvalue_map():
    server = DummyServer()
    assert mod.checkvalue(server, ("map",), "/Game/Maps/ConanSandbox") == "/Game/Maps/ConanSandbox"


def test_checkvalue_servername():
    server = DummyServer()
    assert mod.checkvalue(server, ("servername",), "AlphaGSM Conan") == "AlphaGSM Conan"


def test_checkvalue_exe_name():
    server = DummyServer()
    assert mod.checkvalue(server, ("exe_name",), "ConanSandboxServer.exe") == "ConanSandboxServer.exe"


def test_checkvalue_dir():
    server = DummyServer()
    assert mod.checkvalue(server, ("dir",), "/srv/conan/") == "/srv/conan/"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {
        "profiles": {"default": {"targets": ["saves"]}},
        "schedule": [("default", 0, "days")],
    }
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
