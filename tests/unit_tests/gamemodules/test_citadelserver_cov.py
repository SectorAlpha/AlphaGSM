"""Full coverage tests for citadelserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.citadelserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.citadelserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


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
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "CitadelServer.sh"
    server.data["Steam_AppID"] = 489650
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 489650
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 489650
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 489650
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
    server.data["exe_name"] = "CitadelServer.sh"
    (tmp_path / "CitadelServer.sh").write_text("")
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./CitadelServer.sh",
        "test",
        "-Port=27015",
        "-QueryPort=27015",
        "-MaxPlayers=27015",
        "-ServerName=test",
        "-log",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_falls_back_to_nested_linux_binary(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "missing-wrapper.sh"
    nested = tmp_path / "Citadel" / "Binaries" / "Linux"
    nested.mkdir(parents=True)
    (nested / "CitadelServer-Linux-Shipping").write_text("")
    server.data["map"] = "rook"
    server.data["maxplayers"] = 10
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["servername"] = "fallback"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./Citadel/Binaries/Linux/CitadelServer-Linux-Shipping",
        "Citadel",
        "rook",
        "-Port=7777",
        "-QueryPort=27015",
        "-MaxPlayers=10",
        "-ServerName=fallback",
        "-log",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_prefers_nested_linux_binary_over_wrapper(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "CitadelServer.sh"
    (tmp_path / "CitadelServer.sh").write_text("")
    nested = tmp_path / "Citadel" / "Binaries" / "Linux"
    nested.mkdir(parents=True)
    (nested / "CitadelServer-Linux-Shipping").write_text("")
    server.data["map"] = "rook"
    server.data["maxplayers"] = 10
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["servername"] = "fallback"

    cmd, _cwd = mod.get_start_command(server)

    assert cmd[0] == "./Citadel/Binaries/Linux/CitadelServer-Linux-Shipping"
    assert cmd[1] == "Citadel"


def test_get_runtime_requirements_mounts_server_and_steamcmd_dir(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path)
    with patch.object(mod.steamcmd, "STEAMCMD_DIR", "/var/lib/steamcmd"):
        requirements = mod.get_runtime_requirements(server)

    assert requirements["mounts"] == [
        {"source": str(tmp_path), "target": "/srv/server", "mode": "rw"},
        {"source": "/var/lib/steamcmd", "target": "/opt/alphagsm-steamcmd", "mode": "ro"},
    ]


def test_get_container_spec_runs_as_non_root_with_steam_bootstrap(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path)
    server.data["exe_name"] = "CitadelServer.sh"
    (tmp_path / "CitadelServer.sh").write_text("")
    nested = tmp_path / "Citadel" / "Binaries" / "Linux"
    nested.mkdir(parents=True)
    (nested / "CitadelServer-Linux-Shipping").write_text("")
    server.data["map"] = "rook"
    server.data["maxplayers"] = 50
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["servername"] = "AlphaGSM Citadel"

    with patch.object(mod.steamcmd, "STEAMCMD_DIR", "/var/lib/steamcmd"):
        spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server"
    assert spec["stdin_open"] is True
    assert spec["tty"] is False
    assert spec["mounts"] == [
        {"source": str(tmp_path), "target": "/srv/server", "mode": "rw"},
        {"source": "/var/lib/steamcmd", "target": "/opt/alphagsm-steamcmd", "mode": "ro"},
    ]
    assert spec["command"][:2] == ["sh", "-lc"]
    shell_command = spec["command"][2]
    assert "mkdir -p /home/alphagsm/.steam/sdk64" in shell_command
    assert "ln -sfn /opt/alphagsm-steamcmd/linux64/steamclient.so /home/alphagsm/.steam/sdk64/steamclient.so" in shell_command
    assert "exec runuser -u alphagsm -- sh -lc" in shell_command
    assert (
        "./Citadel/Binaries/Linux/CitadelServer-Linux-Shipping Citadel rook "
        "-Port=7777 -QueryPort=27015 -MaxPlayers=50"
    ) in shell_command
    assert "-ServerName=AlphaGSM Citadel" in shell_command
    assert shell_command.endswith(" -log'")


def test_setting_schema_exposes_citadel_launch_formats():
    assert mod.setting_schema["map"].launch_arg_format == "{value}"
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "-MaxPlayers={value}"
    assert mod.setting_schema["servername"].launch_arg_format == "-ServerName={value}"


def test_query_and_info_addresses_use_tcp_game_port():
    server = DummyServer()
    server.data["port"] = 7777
    assert mod.get_query_address(server) == ("127.0.0.1", 7777, "tcp")
    assert mod.get_info_address(server) == ("127.0.0.1", 7777, "tcp")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
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
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_map():
    server = DummyServer()
    result = mod.checkvalue(server, ("map",), "/test/value")
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
