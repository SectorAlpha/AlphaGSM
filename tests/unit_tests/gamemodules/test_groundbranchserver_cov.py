"""Full coverage tests for groundbranchserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.groundbranchserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.groundbranchserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data['bindaddress'] == '0.0.0.0'


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


def test_install(tmp_path, monkeypatch):
    monkeypatch.setattr(mod.steamcmd, "download", MagicMock())
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "GroundBranchServer-Win64-Shipping.exe"
    server.data["Steam_AppID"] = 476400
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(mod.steamcmd, "download", MagicMock())
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 476400
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(mod.steamcmd, "download", MagicMock())
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 476400
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(mod.steamcmd, "download", MagicMock())
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 476400
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
    server.data["exe_name"] = "GroundBranchServer-Win64-Shipping.exe"
    (tmp_path / "GroundBranchServer-Win64-Shipping.exe").write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "GroundBranchServer-Win64-Shipping.exe",
        "?MaxPlayers=27015",
        "MultiHome=0.0.0.0",
        "Port=27015",
        "QueryPort=27015",
        "-log",
    ]
    assert cwd == server.data["dir"]


def test_linux_launch_uses_xvfb_and_proton_without_xalia(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/xvfb-run")
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda cmd, **_kwargs: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "PROTON_USE_XALIA=0",
            "proton",
            "run",
            *cmd,
        ],
    )
    monkeypatch.setattr(
        mod.proton,
        "prepend_env_assignments",
        lambda cmd, **env: [
            cmd[0],
            *(f"{key}={value}" for key, value in env.items()),
            *cmd[1:],
        ],
    )
    server = DummyServer()
    server.data.update(
        dir=str(tmp_path),
        exe_name="GroundBranchServer-Win64-Shipping.exe",
        port=7777,
        queryport=27015,
        maxplayers=16,
    )
    (tmp_path / server.data["exe_name"]).touch()

    command, _cwd = mod.get_start_command(server)

    assert command[:4] == [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        "env",
    ]
    assert "WINEDLLOVERRIDES=" in command
    assert "PROTON_USE_XALIA=0" in command


def test_setting_schema_exposes_groundbranch_launch_formats():
    assert mod.setting_schema["bindaddress"].launch_arg_format == "MultiHome={value}"
    assert mod.setting_schema["port"].launch_arg_format == "Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "QueryPort={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "?MaxPlayers={value}"


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


def test_native_launch_uses_url_player_option_before_port_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data.update(dir=str(tmp_path), exe_name="GroundBranchServer-Win64-Shipping.exe",
                       port=19000, queryport=19001, maxplayers=12)
    (tmp_path / server.data["exe_name"]).touch()
    command, _cwd = mod.get_start_command(server)
    assert command == [server.data["exe_name"], "?MaxPlayers=12", "MultiHome=0.0.0.0", "Port=19000",
                       "QueryPort=19001", "-log"]


def test_declared_udp_endpoint_uses_runtime_host_and_game_port(monkeypatch):
    server = DummyServer()
    server.data.update(port=19000, queryport=19001)
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda server: "192.0.2.7")
    assert mod.get_query_address(server) == ("192.0.2.7", 19000, "udp")
    assert mod.get_info_address(server) == ("192.0.2.7", 19000, "udp")


def test_runtime_builders_publish_only_native_udp_listeners(monkeypatch):
    server = DummyServer()
    requirements = MagicMock(return_value={})
    spec = MagicMock(return_value={})
    monkeypatch.setattr(mod.proton, "get_runtime_requirements", requirements)
    monkeypatch.setattr(mod.proton, "get_container_spec", spec)
    mod.get_runtime_requirements(server)
    mod.get_container_spec(server)
    for call in (requirements.call_args, spec.call_args):
        assert call.kwargs["port_definitions"] == (
            {"key": "queryport", "protocol": "udp"},
            {"key": "port", "protocol": "udp"},
        )
