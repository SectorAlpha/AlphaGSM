"""Full coverage tests for ecoserver."""

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.ecoserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.ecoserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=3000, dir=str(tmp_path))
    assert server.data['port'] == 3000


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 3000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["storage"] = "test"
    server.data["world"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["3001", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "EcoServer"
    server.data["Steam_AppID"] = 739590
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 739590
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 739590
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 739590
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
    server.data["exe_name"] = "EcoServer"
    (tmp_path / "EcoServer").write_text("")
    linux64_dir = tmp_path / "linux64"
    linux64_dir.mkdir()
    (linux64_dir / "steamclient.so").write_text("")
    server.data["port"] = 27015
    server.data["storage"] = "test"
    server.data["world"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cmd[0] == "env"
    assert "-offline" in cmd
    assert (tmp_path / ".steam" / "sdk64" / "steamclient.so").is_symlink()


def test_sync_server_config_writes_network_ports(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 32000
    config_dir = tmp_path / "Configs"
    config_dir.mkdir()
    (config_dir / "Network.eco.template").write_text(
        json.dumps({"Name": "Eco", "GameServerPort": 3000}),
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    written = json.loads((config_dir / "Network.eco").read_text(encoding="utf-8"))
    assert written["GameServerPort"] == 32000
    assert written["WebServerPort"] == 32001
    assert written["RconServerPort"] == 32002
    assert written["SteamServerPort"] == 32003


def test_install_seeds_local_steam_bootstrap(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "EcoServer"
    server.data["port"] = 3000
    linux64_dir = tmp_path / "linux64"
    linux64_dir.mkdir()
    (linux64_dir / "steamclient.so").write_text("")
    server.data["Steam_AppID"] = 739590
    server.data["Steam_anonymous_login_possible"] = True

    mod.install(server)

    assert (tmp_path / "steam_appid.txt").read_text(encoding="utf-8").strip() == "739590"
    assert (tmp_path / ".steam" / "sdk64" / "steamclient.so").is_symlink()


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["storage"] = "test"
    server.data["world"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    with patch.object(mod.runtime_module, "send_to_server") as send_mock:
        mod.do_stop(server, 0)
    send_mock.assert_called_with(server, "\nsave\nshutdown\n")


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


def test_checkvalue_world():
    server = DummyServer()
    result = mod.checkvalue(server, ("world",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_storage():
    server = DummyServer()
    result = mod.checkvalue(server, ("storage",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_get_runtime_requirements_declares_side_ports_and_libgdiplus():
    server = DummyServer()
    server.data["dir"] = "/srv/eco/"
    server.data["port"] = 32000

    requirements = mod.get_runtime_requirements(server)

    dependency = requirements["host_dependencies"][0]
    assert dependency["id"] == "libgdiplus"
    assert "libgdiplus" in dependency["install_hints"]["linux"]
    assert {"host": 32000, "container": 32000, "protocol": "udp"} in requirements["ports"]
    assert {"host": 32000, "container": 32000, "protocol": "tcp"} in requirements["ports"]
    assert {"host": 32001, "container": 32001, "protocol": "tcp"} in requirements["ports"]
    assert {"host": 32002, "container": 32002, "protocol": "tcp"} in requirements["ports"]
    assert {"host": 32003, "container": 32003, "protocol": "udp"} in requirements["ports"]


def test_get_container_spec_sets_home_and_ld_library_path(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "EcoServer"
    server.data["port"] = 32000
    server.data["world"] = "eco"
    server.data["storage"] = "Storage"
    (tmp_path / "EcoServer").write_text("")

    spec = mod.get_container_spec(server)

    assert spec["env"] == {}
    assert "HOME=." in spec["command"]
    assert "LD_LIBRARY_PATH=.:./linux64" in spec["command"]
    assert "DOTNET_BUNDLE_EXTRACT_BASE_DIR=.net-bundle-cache" in spec["command"]


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
