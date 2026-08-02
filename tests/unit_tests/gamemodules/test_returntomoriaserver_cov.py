"""Full coverage tests for returntomoriaserver."""

import sys
import signal
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.returntomoriaserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.returntomoriaserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data["advertiseaddress"] == "local"
    assert server.data["worldname"] == "Dedicated Server World"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["advertiseport"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "MoriaServer.exe"
    server.data["Steam_AppID"] = 3349480
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3349480
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3349480
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3349480
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
    server.data["exe_name"] = "MoriaServer.exe"
    (tmp_path / "MoriaServer.exe").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_prefers_proton_on_linux(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "MoriaServer.exe",
            "wineprefix": "/srv/return-to-moria-prefix",
        }
    )
    (tmp_path / "MoriaServer.exe").write_text("")

    with (
        patch.object(mod, "IS_LINUX", True),
        patch.object(
            mod.proton,
            "wrap_command",
            return_value=["proton", "run", "MoriaServer.exe"],
        ) as wrap_command,
    ):
        cmd, cwd = mod.get_start_command(server)

    wrap_command.assert_called_once_with(
        ["MoriaServer.exe"],
        wineprefix="/srv/return-to-moria-prefix",
        prefer_proton=True,
    )
    assert cmd == ["proton", "run", "MoriaServer.exe"]
    assert cwd == server.data["dir"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    with (
        patch.object(mod, "IS_LINUX", False),
        patch.object(mod.runtime_module, "send_to_server") as mock_send,
    ):
        mod.do_stop(server, 0)
    mock_send.assert_called_with(server, "\003")


def test_do_stop_linux_targets_real_server_process():
    server = DummyServer()
    server.data["dir"] = "/srv/rtm/"
    with (
        patch.object(mod, "IS_LINUX", True),
        patch.object(mod, "_find_linux_server_pids", return_value=[1234, 5678]),
        patch.object(mod.os, "kill") as mock_kill,
    ):
        mod.do_stop(server, 0)
    assert mock_kill.call_args_list == [
        ((1234, signal.SIGINT),),
        ((5678, signal.SIGINT),),
    ]


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


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "AlphaGSM Dwarves")
    assert result == "AlphaGSM Dwarves"


def test_checkvalue_advertiseaddress():
    server = DummyServer()
    result = mod.checkvalue(server, ("advertiseaddress",), "auto")
    assert result == "auto"


def test_sync_server_config_creates_managed_file(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 35389,
            "advertiseaddress": "local",
            "worldname": "AlphaGSM Dwarves",
        }
    )

    mod.sync_server_config(server)

    config_path = tmp_path / "MoriaServerConfig.ini"
    config_text = config_path.read_text(encoding="utf-8")
    assert "ListenPort=35389" in config_text
    assert "AdvertiseAddress=local" in config_text
    assert "AdvertisePort=35389" in config_text
    assert 'Name="AlphaGSM Dwarves"' in config_text
    assert "Enabled=true" in config_text


def test_query_and_info_addresses_use_game_udp_port():
    server = DummyServer()
    server.data["port"] = 35389
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 35389, "udp")
        assert mod.get_info_address(server) == ("127.0.0.1", 35389, "udp")


def test_runtime_requirements_prefer_proton_and_publish_udp_port():
    server = DummyServer()
    server.data.update({"dir": "/srv/return-to-moria/", "port": 35389})

    requirements = mod.get_runtime_requirements(server)

    assert requirements["family"] == "wine-proton"
    assert requirements["env"]["ALPHAGSM_PREFER_PROTON"] == "1"
    assert requirements["ports"] == [
        {"host": 35389, "container": 35389, "protocol": "udp"}
    ]


def test_runtime_requirements_enable_virtual_display_for_windows_server():
    server = DummyServer()

    requirements = mod.get_runtime_requirements(server)

    assert requirements["env"].items() >= {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 1024x768x24 -nolisten tcp",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }.items()


def test_container_spec_prefers_proton_and_preserves_launch_contract(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "MoriaServer.exe",
            "port": 35389,
        }
    )
    (tmp_path / "MoriaServer.exe").write_text("")

    spec = mod.get_container_spec(server)

    assert spec["env"]["ALPHAGSM_PREFER_PROTON"] == "1"
    assert spec["command"] == ["./MoriaServer.exe"]
    assert spec["working_dir"] == "/srv/server"
    assert spec["stop_mode"] == "exec-console"
    assert spec["stdin_open"] is True
    assert spec["ports"] == [
        {"host": 35389, "container": 35389, "protocol": "udp"}
    ]


def test_find_linux_server_pids_matches_install_marker():
    server = DummyServer()
    server.data["dir"] = "/srv/returntomoriaserver-server/"
    sample = (
        "45163 Z:\\srv\\returntomoriaserver-server\\Moria\\Binaries\\Win64\\"
        "MoriaServer-Win64-Shipping.exe Moria\n"
        "45164 Z:\\srv\\other-server\\Moria\\Binaries\\Win64\\"
        "MoriaServer-Win64-Shipping.exe Moria\n"
    )
    with (
        patch.object(mod, "IS_LINUX", True),
        patch.object(mod.subprocess, "check_output", return_value=sample),
    ):
        assert mod._find_linux_server_pids(server) == [45163]
