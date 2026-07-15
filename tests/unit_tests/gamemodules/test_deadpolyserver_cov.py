"""Full coverage tests for deadpolyserver."""

import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.deadpolyserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.deadpolyserver as mod
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
    server.data["maxplayers"] = 27015
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
    server.data["exe_name"] = "DeadPolyServer.exe"
    server.data["Steam_AppID"] = 2208380
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2208380
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2208380
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2208380
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
    server.data["exe_name"] = "DeadPolyServer.exe"
    (tmp_path / "DeadPolyServer.exe").write_text("")
    server.data["servername"] = "AlphaGSM DeadPoly"
    server.data["maxplayers"] = 24
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    with patch.object(
        mod.proton,
        "wrap_command",
        side_effect=lambda command, **_kwargs: command,
    ):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "DeadPolyServer.exe",
        "-log",
        "-nosteam",
        "-port=27015",
        "-queryport=27016",
        "-maxplayers=24",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_deadpoly_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-queryport={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "-maxplayers={value}"


def test_sync_server_config_stages_and_rewrites_game_ini(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["servername"] = "AlphaGSM DeadPoly"
    server.data["maxplayers"] = 32
    seed_dir = tmp_path / "DeadPoly" / "Saved" / "1 RENAME Config" / "WindowsServer"
    seed_dir.mkdir(parents=True)
    seed_ini = seed_dir / "Game.ini"
    seed_ini.write_text(
        "ServerName=DeadPoly Server\n"
        "PlayerSlots=20\n"
        "Admins=76561198000000001\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    config_path = tmp_path / "DeadPoly" / "Saved" / "Config" / "WindowsServer" / "Game.ini"
    text = config_path.read_text(encoding="utf-8")
    assert "ServerName=AlphaGSM DeadPoly" in text
    assert "PlayerSlots=32" in text
    assert "Admins=76561198000000001" in text


def test_sync_server_config_no_seed_is_noop(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["servername"] = "AlphaGSM DeadPoly"
    server.data["maxplayers"] = 32

    mod.sync_server_config(server)

    config_path = tmp_path / "DeadPoly" / "Saved" / "Config" / "WindowsServer" / "Game.ini"
    assert not config_path.exists()


def test_get_query_and_info_address():
    server = DummyServer()
    server.data["queryport"] = 27016
    expected = ("127.0.0.1", 27016, "tcp")
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
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
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


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
