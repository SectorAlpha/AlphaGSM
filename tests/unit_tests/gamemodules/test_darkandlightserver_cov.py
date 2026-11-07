"""Full coverage tests for darkandlightserver."""

import os
import signal
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.darkandlightserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.darkandlightserver as mod
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
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DNL/Binaries/Win64/DNLServer.exe"
    server.data["Steam_AppID"] = 630230
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 630230
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 630230
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 630230
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
    server.data["exe_name"] = "DNL/Binaries/Win64/DNLServer.exe"
    exe_path = tmp_path / "DNL/Binaries/Win64/DNLServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "DNL/Binaries/Win64/DNLServer.exe",
        "test?listen?SessionName=test?ServerPassword=test?ServerAdminPassword=test?Port=27015?QueryPort=27015?MaxPlayers=27015",
        "-nullRHI",
        "-log",
        "-unattended",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_uses_nested_dnl_install_root(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    nested_root = tmp_path / "DNL Dedicated Server"
    exe_path = nested_root / "DNL" / "Binaries" / "Win64" / "DNLServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DNL/Binaries/Win64/DNLServer.exe"
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["startmap"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "DNL Dedicated Server/DNL/Binaries/Win64/DNLServer.exe"
    assert cwd == server.data["dir"]


def test_get_start_command_prefers_nested_dnl_install_root_over_top_level_payload(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    nested_root = tmp_path / "DNL Dedicated Server"
    nested_exe = nested_root / "DNL" / "Binaries" / "Win64" / "DNLServer.exe"
    nested_exe.parent.mkdir(parents=True, exist_ok=True)
    nested_exe.write_text("")
    top_level_exe = tmp_path / "DNL" / "Binaries" / "Win64" / "DNLServer.exe"
    top_level_exe.parent.mkdir(parents=True, exist_ok=True)
    top_level_exe.write_text("")
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DNL/Binaries/Win64/DNLServer.exe"
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["startmap"] = "test"

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "DNL Dedicated Server/DNL/Binaries/Win64/DNLServer.exe"
    assert cwd == server.data["dir"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["serverpassword"] = "test"
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_query_and_info_address_use_game_port_udp_on_linux(monkeypatch):
    server = DummyServer("dnl")
    server.data["port"] = "34121"
    server.data["queryport"] = "27016"
    monkeypatch.setattr(mod, "IS_LINUX", True)
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 34121, "udp")
    assert mod.get_info_address(server) == ("10.0.0.10", 34121, "udp")


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


def test_do_stop_targets_linux_server_processes(monkeypatch):
    server = DummyServer("dnl")
    server.data["exe_name"] = "DNL/Binaries/Win64/DNLServer.exe"
    server.data["port"] = 33741
    server.data["queryport"] = 27016
    killed = []

    mod.runtime_module.send_to_server.reset_mock()
    monkeypatch.setattr(mod, "IS_LINUX", True)
    monkeypatch.setattr(
        mod,
        "_find_linux_server_pids",
        lambda current: [4321, 5432],
    )
    monkeypatch.setattr(mod.os, "kill", lambda pid, sig: killed.append((pid, sig)))

    mod.do_stop(server, 0)

    assert killed == [(4321, signal.SIGTERM), (5432, signal.SIGTERM)]
    mod.runtime_module.send_to_server.assert_not_called()


def test_runtime_requirements_enable_xvfb_container_env():
    server = DummyServer()
    server.data["dir"] = "/srv/dnl/"
    server.data["port"] = 7777
    server.data["queryport"] = 27016

    requirements = mod.get_runtime_requirements(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert requirements["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"


def test_find_linux_server_pids_filters_for_matching_commandline(monkeypatch):
    server = DummyServer("dnl")
    server.data["exe_name"] = "DNL/Binaries/Win64/DNLServer.exe"
    server.data["port"] = 33741
    server.data["queryport"] = 27016
    ps_output = "\n".join(
        [
            "1111 env proton run DNL/Binaries/Win64/DNLServer.exe DNL_ALL?Port=33741?QueryPort=27016",
            "2222 env proton run DNL/Binaries/Win64/DNLServer.exe DNL_ALL?Port=33742?QueryPort=27016",
            "3333 other.exe Port=33741 QueryPort=27016",
        ]
    )

    monkeypatch.setattr(mod.subprocess, "check_output", lambda *args, **kwargs: ps_output)

    assert mod._find_linux_server_pids(server) == [1111]


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


def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "/test/value")
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
