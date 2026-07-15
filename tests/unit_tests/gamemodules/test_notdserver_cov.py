"""Full coverage tests for notdserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.notdserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.notdserver as mod
    from server import ServerError


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
    server.data["exe_name"] = "LF/Binaries/Win64/LFServer.exe"
    server.data["Steam_AppID"] = 1420710
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1420710
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1420710
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1420710
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
    server.data["exe_name"] = "LF/Binaries/Win64/LFServer.exe"
    exe_path = tmp_path / "LF/Binaries/Win64/LFServer.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "LF/Binaries/Win64/LFServer.exe",
        "?listen",
        "-Port=27015",
        "-QueryPort=27015",
        "-log",
        "-CRASHREPORTS",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_linux_adds_disable_anticheat_and_wraps(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: ["wrapped", *cmd],
    )
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "LFServer.exe"
    exe_path = tmp_path / "LFServer.exe"
    exe_path.write_text("")
    server.data["port"] = 7777
    server.data["queryport"] = 27015

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "wrapped",
        "LFServer.exe",
        "?listen",
        "-DisableAntiCheat",
        "-Port=7777",
        "-QueryPort=27015",
        "-log",
        "-CRASHREPORTS",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_notd_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"


def test_notdserver_runtime_metadata_enables_xvfb_for_docker(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LFServer.exe",
            "port": 7777,
            "queryport": 27015,
        }
    )
    (tmp_path / "LFServer.exe").write_text("")

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert spec["env"]["ALPHAGSM_XVFB"] == "1"
    assert spec["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_once_with(server, "\003")


def test_sync_server_config_copies_root_settings_ini(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    source = tmp_path / "ServerSettings.ini"
    source.write_text("[ServerSettings]\nServerName=AlphaGSM\n")

    mod.sync_server_config(server)

    copied = tmp_path / "LF" / "Saved" / "Config" / "ServerSettings.ini"
    assert copied.read_text() == source.read_text()


def test_prestart_calls_sync_server_config(monkeypatch):
    server = DummyServer()
    calls = []
    monkeypatch.setattr(mod, "sync_server_config", lambda current: calls.append(current))

    mod.prestart(server)

    assert calls == [server]


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
