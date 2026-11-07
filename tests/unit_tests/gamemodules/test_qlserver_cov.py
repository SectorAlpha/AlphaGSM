"""Full coverage tests for qlserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.qlserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.qlserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27960, dir=str(tmp_path))
    assert server.data['port'] == 27960


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27960
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["hostname"] = "test"
    server.data["servercfg"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27961", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "qzeroded.x64"
    server.data["Steam_AppID"] = 349090
    server.data["Steam_anonymous_login_possible"] = True
    server.data["servercfg"] = "baseq3/server.cfg"
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 349090
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 349090
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 349090
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
    server.data["exe_name"] = "qzeroded.x64"
    (tmp_path / "qzeroded.x64").write_text("")
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["servercfg"] = "test"
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "env",
        "LD_LIBRARY_PATH=./linux64",
        "./qzeroded.x64",
        "+set",
        "fs_game",
        "baseq3",
        "+set",
        "fs_homepath",
        server.data["dir"],
        "+set",
        "net_port",
        "27015",
        "+set",
        "sv_hostname",
        "test",
        "+exec",
        "test",
        "+set",
        "serverstartup",
        "map test ffa",
        "+set",
        "net_ip",
        "0.0.0.0",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_uses_container_paths_for_docker(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "qzeroded.x64"
    server.data["runtime"] = "docker"
    (tmp_path / "qzeroded.x64").write_text("")
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["servercfg"] = "test"
    server.data["startmap"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "env",
        "LD_LIBRARY_PATH=./linux64",
        "./qzeroded.x64",
        "+set",
        "fs_game",
        "baseq3",
        "+set",
        "fs_homepath",
        "/srv/server",
        "+set",
        "net_port",
        "27015",
        "+set",
        "sv_hostname",
        "test",
        "+exec",
        "test",
        "+set",
        "serverstartup",
        "map test ffa",
        "+set",
        "net_ip",
        "0.0.0.0",
    ]
    assert cwd == server.data["dir"]


def test_get_container_spec_uses_container_homepath(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "qzeroded.x64"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["servercfg"] = "server.cfg"
    server.data["startmap"] = "campgrounds"

    spec = mod.get_container_spec(server)

    assert spec["command"] == [
        "env",
        "LD_LIBRARY_PATH=./linux64",
        "./qzeroded.x64",
        "+set",
        "fs_game",
        "baseq3",
        "+set",
        "fs_homepath",
        "/srv/server",
        "+set",
        "net_port",
        "27015",
        "+set",
        "sv_hostname",
        "test",
        "+exec",
        "server.cfg",
        "+set",
        "serverstartup",
        "map campgrounds ffa",
        "+set",
        "net_ip",
        "0.0.0.0",
    ]


@pytest.mark.parametrize("exe_name, library_dir", [
    ("qzeroded.x64", "./linux64"),
    ("qzeroded.x86", "./linux32"),
    ("custom-qzeroded.x64", "./linux64"),
])
def test_launchers_use_bundled_steam_library_for_selected_binary(tmp_path, exe_name, library_dir):
    server = DummyServer()
    mod.configure(server, ask=False, port=27960, dir=str(tmp_path), exe_name=exe_name)
    (tmp_path / exe_name).write_bytes(b"mock executable")

    process_command, process_cwd = mod.get_start_command(server)
    spec = mod.get_container_spec(server)

    for command in (process_command, spec["command"]):
        assert command[:3] == ["env", "LD_LIBRARY_PATH=" + library_dir, "./" + exe_name]
    assert process_cwd == server.data["dir"]
    assert spec["working_dir"] == "/srv/server"
    assert process_command[process_command.index("fs_homepath") + 1] == server.data["dir"]
    assert spec["command"][spec["command"].index("fs_homepath") + 1] == "/srv/server"


def test_setting_schema_exposes_quake_live_launch_tokens():
    assert mod.setting_schema["port"].launch_arg_tokens == ("+set", "net_port")
    assert mod.setting_schema["hostname"].launch_arg_tokens == ("+set", "sv_hostname")
    assert mod.setting_schema["startmap"].aliases == ("map",)
    assert mod.setting_schema["homepath"].storage_key == "dir"
    assert mod.setting_schema["servercfg"].launch_arg_tokens == ("+exec",)


def test_sync_server_config_updates_quake_live_server_cfg(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["servercfg"] = "baseq3/server.cfg"
    server.data["hostname"] = "AlphaGSM QL Test"
    server.data["startmap"] = "asylum"
    config_dir = tmp_path / "baseq3"
    config_dir.mkdir()
    config_path = config_dir / "server.cfg"
    config_path.write_text(
        'hostname="Old Name"\n'
        'startmap=campgrounds\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        'set sv_hostname "AlphaGSM QL Test"',
        'set serverstartup "map asylum ffa"',
        'set net_ip "0.0.0.0"',
    ]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["servercfg"] = "test"
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_with(server, "\nquit\n")


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


def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "campgrounds")
    assert result == "campgrounds"


def test_checkvalue_servercfg():
    server = DummyServer()
    result = mod.checkvalue(server, ("servercfg",), "/test/value")
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
