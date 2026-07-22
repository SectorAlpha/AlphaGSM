"""Full coverage tests for astroneerserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.astroneerserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.astroneerserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=8777, dir=str(tmp_path))
    assert server.data['port'] == 8777
    assert server.data["exe_name"] == "Astro/Binaries/Win64/AstroServer-Win64-Shipping.exe"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["ownername"] = "test"
    server.data["publicip"] = "test"
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "AstroServer.exe"
    server.data["Steam_AppID"] = 728470
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_sync_server_config_writes_official_astroneer_ini_files(tmp_path):
    server = DummyServer("astro")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 28777,
            "publicip": "203.0.113.10",
            "ownername": "AlphaOwner",
        }
    )

    mod.sync_server_config(server)

    config_dir = tmp_path / "Astro" / "Saved" / "Config" / "WindowsServer"
    assert (config_dir / "Engine.ini").read_text(encoding="utf-8") == (
        "[URL]\n"
        "Port=28777\n"
        "\n"
        "[SystemSettings]\n"
        "net.AllowEncryption=False\n"
    )
    assert (config_dir / "AstroServerSettings.ini").read_text(
        encoding="utf-8"
    ) == (
        "PublicIP=203.0.113.10\n"
        "OwnerName=AlphaOwner\n"
        "OwnerGuid=0\n"
    )
    assert mod.config_sync_keys == ("port", "publicip", "ownername")


def test_sync_server_config_rewrites_generated_astroneer_server_settings(tmp_path):
    server = DummyServer("astro")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 28777,
            "publicip": "203.0.113.10",
            "ownername": "AlphaOwner",
        }
    )
    config_dir = tmp_path / "Astro" / "Saved" / "Config" / "WindowsServer"
    config_dir.mkdir(parents=True)
    settings_path = config_dir / "AstroServerSettings.ini"
    settings_path.write_text(
        "[/Script/Astro.AstroServerSettings]\n"
        "PublicIP=\n"
        "ServerName=\n"
        "OwnerName=\n"
        "OwnerGuid=0\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    settings = settings_path.read_text(encoding="utf-8")
    assert "[/Script/Astro.AstroServerSettings]\n" in settings
    assert "PublicIP=203.0.113.10\n" in settings
    assert "OwnerName=AlphaOwner\n" in settings
    assert "OwnerGuid=0\n" in settings


def test_sync_server_config_defaults_blank_astroneer_registration_values(tmp_path):
    server = DummyServer("astro")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 28777,
            "publicip": "",
            "ownername": "",
        }
    )
    config_dir = tmp_path / "Astro" / "Saved" / "Config" / "WindowsServer"
    config_dir.mkdir(parents=True)
    settings_path = config_dir / "AstroServerSettings.ini"
    settings_path.write_text(
        "[/Script/Astro.AstroServerSettings]\n"
        "PublicIP=\n"
        "OwnerName=\n"
        "OwnerGuid=0\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    settings = settings_path.read_text(encoding="utf-8")
    assert "PublicIP=127.0.0.1\n" in settings
    assert "OwnerName=AlphaGSM\n" in settings


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 728470
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 728470
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 728470
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command_prefers_shipping_executable_for_legacy_launcher(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "AstroServer.exe"
    (tmp_path / "AstroServer.exe").write_text("")
    shipping_exe = "Astro/Binaries/Win64/AstroServer-Win64-Shipping.exe"
    shipping_path = tmp_path / shipping_exe
    shipping_path.parent.mkdir(parents=True)
    shipping_path.write_text("")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == ["AstroServer-Win64-Shipping.exe"]
    assert cwd == str(shipping_path.parent)


def test_get_start_command_keeps_legacy_launcher_until_shipping_payload_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "AstroServer.exe"
    (tmp_path / "AstroServer.exe").write_text("")

    cmd, _cwd = mod.get_start_command(server)

    assert cmd == ["AstroServer.exe"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop(monkeypatch):
    server = DummyServer()
    send_mock = MagicMock()
    monkeypatch.setattr(mod.runtime_module, "send_to_server", send_mock)
    mod.do_stop(server, 0)
    send_mock.assert_called_with(server, "\003")


def test_query_info_and_runtime_ports_use_udp_on_main_port(monkeypatch):
    server = DummyServer()
    server.data["port"] = 8777
    monkeypatch.setattr(
        mod.runtime_module,
        "resolve_query_host",
        lambda current: "10.0.0.8",
    )

    assert mod.get_query_address(server) == ("10.0.0.8", 8777, "udp")
    assert mod.get_info_address(server) == ("10.0.0.8", 8777, "udp")
    assert mod.get_runtime_requirements(server)["ports"] == [
        {"host": 8777, "container": 8777, "protocol": "udp"},
    ]
    assert mod.get_runtime_requirements(server)["env"]["ALPHAGSM_PREFER_PROTON"] == "1"


def test_container_spec_uses_same_game_command_and_udp_port(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer("astro")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "AstroServer.exe",
            "port": 8777,
        }
    )
    (tmp_path / "AstroServer.exe").write_text("")
    shipping_exe = "Astro/Binaries/Win64/AstroServer-Win64-Shipping.exe"
    shipping_path = tmp_path / shipping_exe
    shipping_path.parent.mkdir(parents=True)
    shipping_path.write_text("")

    process_command, _cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    assert process_command == ["AstroServer-Win64-Shipping.exe"]
    assert spec["command"] == ["./AstroServer-Win64-Shipping.exe"]
    assert spec["working_dir"] == "/srv/server/Astro/Binaries/Win64"
    assert spec["ports"] == [
        {"host": 8777, "container": 8777, "protocol": "udp"},
    ]
    assert spec["env"]["ALPHAGSM_PREFER_PROTON"] == "1"


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


def test_checkvalue_publicip():
    server = DummyServer()
    result = mod.checkvalue(server, ("publicip",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_ownername():
    server = DummyServer()
    result = mod.checkvalue(server, ("ownername",), "/test/value")
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
