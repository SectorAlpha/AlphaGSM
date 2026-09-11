"""Full coverage tests for blackops3server."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.blackops3server', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.blackops3server as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, dir=str(tmp_path))
    assert server.data['port'] == 27015


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 28960
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["28961", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "BlackOps3Server.exe"
    server.data["Steam_AppID"] = 545990
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 545990
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 545990
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 545990
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
    server.data["exe_name"] = "BlackOps3Server.exe"
    (tmp_path / "BlackOps3Server.exe").write_text("")
    server.data["maxplayers"] = 18
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "BlackOps3_UnrankedDedicatedServer.exe",
        "+set", "sv_playlist", "1",
        "+set", "fs_game", "usermaps",
        "+set", "logfile", "2",
        "+set", "sv_maxclients", "18",
    ]
    assert cwd == os.path.join(server.data["dir"], "UnrankedServer")


def test_setting_schema_exposes_blackops3_launch_tokens():
    assert mod.setting_schema["port"].apply_to == ("datastore",)
    assert mod.setting_schema["port"].launch_arg_tokens is None
    assert mod.setting_schema["maxplayers"].launch_arg_tokens == ("+set", "sv_maxclients")


def test_runtime_requirements_map_managed_ports_to_fixed_bo3_ports():
    server = DummyServer()
    server.data["port"] = 28000

    assert mod.port_claim_definitions == (
        {"key": "port", "container": 27015, "protocol": "udp"},
        {"key": "port", "container": 27015, "protocol": "tcp"},
        {"key": "port", "offset": 1, "container": 27016, "protocol": "udp"},
        {"key": "port", "offset": 1, "container": 27016, "protocol": "tcp"},
        {"key": "port", "offset": 2, "container": 27017, "protocol": "udp"},
        {"key": "port", "offset": 2, "container": 27017, "protocol": "tcp"},
    )

    requirements = mod.get_runtime_requirements(server)

    assert requirements["ports"] == [
        {"host": 28000, "container": 27015, "protocol": "udp"},
        {"host": 28000, "container": 27015, "protocol": "tcp"},
        {"host": 28001, "container": 27016, "protocol": "udp"},
        {"host": 28001, "container": 27016, "protocol": "tcp"},
        {"host": 28002, "container": 27017, "protocol": "udp"},
        {"host": 28002, "container": 27017, "protocol": "tcp"},
    ]


def test_query_hooks_use_runtime_resolved_managed_udp_port(monkeypatch):
    server = DummyServer()
    server.data["port"] = 28000
    monkeypatch.setattr(
        mod.runtime_module,
        "resolve_query_host",
        lambda server_obj: "172.18.0.13",
    )

    expected = ("172.18.0.13", 28000, "udp")
    assert mod.get_query_address(server) == expected
    assert mod.get_info_address(server) == expected


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
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
