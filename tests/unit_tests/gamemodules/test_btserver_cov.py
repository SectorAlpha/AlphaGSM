"""Full coverage tests for btserver."""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.btserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.btserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["gamemode"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer"
    server.data["Steam_AppID"] = 1026340
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1026340
    server.data["Steam_anonymous_login_possible"] = True
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=True, restart=True)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 1026340, True, validate=True
    )
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1026340
    server.data["Steam_anonymous_login_possible"] = True
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=False, restart=False)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 1026340, True, validate=False
    )
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1026340
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
    server.data["exe_name"] = "DedicatedServer"
    (tmp_path / "DedicatedServer").write_text("")
    server.data["gamemode"] = "Sandbox"
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./DedicatedServer",
        "-name",
        "testserver",
        "-port",
        "27015",
        "-queryport",
        "27016",
        "-gamemode",
        "Sandbox",
    ]
    assert cwd == str(tmp_path)


def test_get_start_command_prefers_symlink_target_within_install_tree(tmp_path):
    server = DummyServer()
    nested_dir = tmp_path / "serverfiles"
    nested_dir.mkdir()
    target = nested_dir / "DedicatedServer"
    target.write_text("", encoding="utf-8")
    os.symlink(target, tmp_path / "DedicatedServer")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer"
    server.data["gamemode"] = "Sandbox"
    server.data["port"] = 27015
    server.data["queryport"] = 27016

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./DedicatedServer"
    assert cwd == str(nested_dir)


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["gamemode"] = "test"
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


def test_get_query_and_info_address_use_runtime_resolved_host():
    server = DummyServer()
    server.data["port"] = 27015
    server.data["queryport"] = 27016

    with patch.object(
        mod.runtime_module,
        "resolve_query_host",
        side_effect=["172.18.0.7", "172.18.0.7"],
    ) as resolve_query_host:
        assert mod.get_query_address(server) == ("172.18.0.7", 27016, "a2s")
        assert mod.get_info_address(server) == ("172.18.0.7", 27016, "a2s")

    assert resolve_query_host.call_args_list == [((server,),), ((server,),)]


def test_get_runtime_requirements_adds_steam_sdk_mounts(monkeypatch, tmp_path):
    steamcmd_root = tmp_path / "Steam"
    linux64 = steamcmd_root / "linux64"
    linux32 = steamcmd_root / "linux32"
    linux64.mkdir(parents=True)
    linux32.mkdir(parents=True)
    (linux64 / "steamclient.so").write_text("64")
    (linux32 / "steamclient.so").write_text("32")
    monkeypatch.setattr(
        mod.runtime_module,
        "steamcmd_module",
        SimpleNamespace(STEAMCMD_DIR=str(steamcmd_root)),
    )

    server = DummyServer()
    server.data["dir"] = str(tmp_path / "server") + "/"
    server.data["port"] = 27015
    server.data["queryport"] = 27016

    requirements = mod.get_runtime_requirements(server)
    mounts = requirements["mounts"]

    assert mounts[0] == {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
    assert mounts[1]["target"] == "/root/.steam/sdk64"
    assert mounts[1]["mode"] == "ro"
    assert os.path.basename(mounts[1]["source"]) == "linux64"
    assert mounts[2]["target"] == "/root/.steam/sdk32"
    assert mounts[2]["mode"] == "ro"
    assert os.path.basename(mounts[2]["source"]) == "linux32"


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


def test_checkvalue_gamemode():
    server = DummyServer()
    result = mod.checkvalue(server, ("gamemode",), "/test/value")
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
