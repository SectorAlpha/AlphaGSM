"""Full coverage tests for valheim."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.valheim', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.valheim as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=2456, dir=str(tmp_path))
    assert server.data['port'] == 2456
    assert server.data["Steam_AppID"] == 896660
    assert server.data["worldname"] == "testserver"
    assert server.data["serverpassword"] == "alphagsm"
    assert server.data["queryport"] == "2457"
    assert server.data["backupfiles"] == ["worlds", "start_server.sh"]


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 2456
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["public"] = True
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["worldname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["2457", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "valheim_server.x86_64"
    server.data["Steam_AppID"] = 896660
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 896660
    server.data["Steam_anonymous_login_possible"] = True
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=True, restart=True)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 896660, True, validate=True
    )
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 896660
    server.data["Steam_anonymous_login_possible"] = True
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=False, restart=False)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 896660, True, validate=False
    )
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 896660
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
    server.data["exe_name"] = "valheim_server.x86_64"
    (tmp_path / "valheim_server.x86_64").write_text("")
    server.data["port"] = 2456
    server.data["public"] = "0"
    server.data["servername"] = "AlphaGSM valheim"
    server.data["serverpassword"] = "alphagsm"
    server.data["worldname"] = "myworld"
    cmd, cwd = mod.get_start_command(server)
    assert cmd[0] == "./valheim_server.x86_64"
    assert "-world" in cmd and cmd[cmd.index("-world") + 1] == "myworld"
    assert "-savedir" in cmd
    assert cwd == str(tmp_path)


def test_get_start_command_prefers_symlink_target_within_install_tree(tmp_path):
    server = DummyServer()
    nested_dir = tmp_path / "linux64"
    nested_dir.mkdir()
    target = nested_dir / "valheim_server.x86_64"
    target.write_text("", encoding="utf-8")
    os.symlink(target, tmp_path / "valheim_server.x86_64")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "valheim_server.x86_64"
    server.data["port"] = 27015
    server.data["public"] = True
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["worldname"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./valheim_server.x86_64"
    assert cwd == str(nested_dir)


def test_get_start_command_uses_relative_savedir_for_docker_runtime(tmp_path):
    server = DummyServer()
    nested_dir = tmp_path / "linux64"
    nested_dir.mkdir()
    target = nested_dir / "valheim_server.x86_64"
    target.write_text("", encoding="utf-8")
    os.symlink(target, tmp_path / "valheim_server.x86_64")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "valheim_server.x86_64"
    server.data["port"] = 27015
    server.data["public"] = True
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["worldname"] = "test"
    server.data["runtime"] = "docker"

    cmd, cwd = mod.get_start_command(server)

    assert cwd == str(nested_dir)
    assert cmd[cmd.index("-savedir") + 1] == "../worlds"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["public"] = True
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["worldname"] = "test"
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


def test_get_info_address_matches_queryport_override():
    server = DummyServer()
    server.data["port"] = 2456
    server.data["queryport"] = 3456

    assert mod.get_query_address(server) == ("127.0.0.1", 3456, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 3456, "a2s")


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
    result = mod.checkvalue(server, ("queryport",), "12346")
    assert result == 12346


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_public():
    server = DummyServer()
    result = mod.checkvalue(server, ("public",), "/test/value")
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
