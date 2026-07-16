"""Full coverage tests for sniperelite4server."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.sniperelite4server', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.sniperelite4server as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data["maxplayers"] == "12"


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
    server.data["exe_name"] = "SniperElite4_DedicatedServer.exe"
    server.data["Steam_AppID"] = 568880
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_sync_server_config_preserves_example_rules_and_manages_ports(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path)
    server.data["port"] = 7777
    server.data["maxplayers"] = 12
    example_cfg = tmp_path / "Docs" / "ExampleConfigs" / "Example1.cfg"
    example_cfg.parent.mkdir(parents=True)
    example_cfg.write_text(
        "MapRotation.AddMap VILLAGE DM\n"
        "Server.GamePort 9999\n"
        "Server.Host\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    config_text = (tmp_path / "default.cfg").read_text(encoding="utf-8")
    assert "MapRotation.AddMap VILLAGE DM" in config_text
    assert "Server.Name testserver" in config_text
    assert "Server.GamePort 7777" in config_text
    assert "Server.AuthPort 7778" in config_text
    assert "Server.UpdatePort 7779" in config_text
    assert "Server.LobbyPort 7780" in config_text
    assert "Settings.MaxPlayers 12" in config_text
    assert config_text.rstrip().endswith("Server.Host")
    assert "Server.GamePort 9999" not in config_text


def test_install_generates_fallback_default_cfg(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path)
    server.data["port"] = 7777
    server.data["maxplayers"] = 12

    mod.sync_server_config(server)

    config_text = (tmp_path / "default.cfg").read_text(encoding="utf-8")
    assert "// AlphaGSM generated default.cfg" in config_text
    assert "Server.GamePort 7777" in config_text
    assert config_text.rstrip().endswith("Server.Host")


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 568880
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 568880
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 568880
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
    server.data["exe_name"] = "SniperElite4_DedicatedServer.exe"
    (tmp_path / "SniperElite4_DedicatedServer.exe").write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "SniperElite4_DedicatedServer.exe",
        "exec",
        "default.cfg",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_syncs_sniperelite4_config_values():
    assert mod.config_sync_keys == ("port", "maxplayers")
    assert mod.setting_schema["port"].apply_to == ("datastore", "config")
    assert mod.setting_schema["maxplayers"].apply_to == ("datastore", "config")
    assert "queryport" not in mod.setting_schema


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


def test_runtime_requirements_enable_xvfb_container_env():
    server = DummyServer()
    server.data["dir"] = "/srv/se4/"
    server.data["port"] = 7777
    server.data["queryport"] = 27015

    requirements = mod.get_runtime_requirements(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert requirements["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"
    assert requirements["ports"] == [
        {"host": 7777, "container": 7777, "protocol": "udp"},
        {"host": 7778, "container": 7778, "protocol": "udp"},
        {"host": 7779, "container": 7779, "protocol": "udp"},
        {"host": 7780, "container": 7780, "protocol": "tcp"},
    ]


def test_query_and_info_use_runtime_resolved_main_udp_port():
    server = DummyServer()
    server.data["port"] = 7777

    with patch.object(
        mod.runtime_module,
        "resolve_query_host",
        side_effect=["172.18.0.12", "172.18.0.12"],
    ) as resolve_query_host:
        assert mod.get_query_address(server) == ("172.18.0.12", 7777, "udp")
        assert mod.get_info_address(server) == ("172.18.0.12", 7777, "udp")

    assert resolve_query_host.call_args_list == [((server,),), ((server,),)]


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
