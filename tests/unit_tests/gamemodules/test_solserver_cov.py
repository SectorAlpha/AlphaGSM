"""Full coverage tests for solserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.solserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.solserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=23073, dir=str(tmp_path))
    assert server.data['port'] == 23073


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 23073
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["hostname"] = "test"
    server.data["maxplayers"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["23074", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "soldatserver"
    server.data["Steam_AppID"] = 638500
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 638500
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 638500
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 638500
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
    server.data["exe_name"] = "soldatserver"
    (tmp_path / "soldatserver").write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_native_soldat_launch_and_query_ports(tmp_path, monkeypatch):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name="soldatserver", port=23080, maxplayers=12)
    (tmp_path / "soldatserver").touch()
    command, cwd = mod.get_start_command(server)
    assert command[command.index("-l") + 1] == "12"
    assert "-maxplayers" not in command
    assert cwd == str(tmp_path)
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda _s: "172.17.0.1")
    assert mod.get_query_address(server) == ("172.17.0.1", 23090, "soldat")
    assert mod.get_info_address(server) == mod.get_query_address(server)


def test_native_soldat_config_preserves_operator_values(tmp_path):
    import configparser
    server = DummyServer()
    server.data.update(dir=str(tmp_path), port=23080, maxplayers=12, hostname="Alpha % World")
    target = tmp_path / "soldat.ini"
    target.write_text("[GAME]\nLogging=0\nDeathmatch_Limit=40\n[NETWORK]\nPort=23073\nAllow_Download=0\nAdmin_Password=keep-this\n")
    mod.sync_server_config(server)
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(target)
    assert parser['NETWORK']['Port'] == '23080'
    assert parser['NETWORK']['Max_Players'] == '12'
    assert parser['NETWORK']['Server_Name'] == 'Alpha % World'
    assert parser['NETWORK']['Admin_Password'] == 'keep-this'
    assert parser['NETWORK']['Allow_Download'] == '1'
    assert parser['GAME']['Logging'] == '1'
    assert parser['GAME']['Deathmatch_Limit'] == '40'


def test_soldat_runtime_uses_host_user_and_publishes_status_port(tmp_path):
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name="soldatserver", port=23080, maxplayers=12)
    (tmp_path / "soldatserver").touch()
    for metadata in (mod.get_runtime_requirements(server), mod.get_container_spec(server)):
        assert metadata['run_as_host_user'] is True
        assert metadata['container_home'] == '/home/alphagsm'
        assert any(p['container'] == 23090 and p['protocol'] == 'tcp' for p in metadata['ports'])


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


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
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
