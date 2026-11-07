"""Full coverage tests for noonesurvivedserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.noonesurvivedserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.noonesurvivedserver as mod
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
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "WRSHServer.exe"
    server.data["Steam_AppID"] = 2329680
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2329680
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2329680
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2329680
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
    server.data["exe_name"] = "WRSHServer.exe"
    (tmp_path / "WRSHServer.exe").write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "WRSHServer.exe",
        "-server",
        "-log",
        "-port=27015",
        "-queryport=27015",
        "-servername=test",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_noonesurvived_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-queryport={value}"
    assert mod.setting_schema["servername"].launch_arg_format == "-servername={value}"


def test_noonesurvived_runtime_metadata_enables_xvfb_for_docker(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "WRSHServer.exe",
            "port": 7777,
            "queryport": 27015,
            "servername": "AlphaGSM noonesurvived",
        }
    )
    (tmp_path / "WRSHServer.exe").write_text("")

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert requirements["env"]["PROTON_USE_XALIA"] == "0"
    assert spec["env"]["ALPHAGSM_XVFB"] == "1"
    assert spec["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"
    assert spec["env"]["PROTON_USE_XALIA"] == "0"


def test_noonesurvived_linux_process_launch_uses_xvfb(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda _name: "/usr/bin/xvfb-run")
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda command, **_kwargs: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "wine",
            *command,
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

    command = mod._wrap_linux_command(["WRSHServer.exe", "-server"])

    assert command[:2] == ["xvfb-run", "-a"]
    assert "DISPLAY=" not in command
    assert "WINEDLLOVERRIDES=winex11.drv=" not in command
    assert "WINEDLLOVERRIDES=" in command
    assert "SDL_VIDEODRIVER=x11" in command
    assert "SDL_AUDIODRIVER=dummy" in command
    assert "PROTON_USE_XALIA=0" in command


@pytest.mark.parametrize(
    "is_linux,expected",
    [
        (True, ("127.0.0.1", 7777, "tcp")),
        (False, ("127.0.0.1", 27015, "a2s")),
    ],
)
def test_query_addresses_use_validated_platform_protocol(monkeypatch, is_linux, expected):
    monkeypatch.setattr(mod, "IS_LINUX", is_linux)
    server = DummyServer()
    server.data.update({"port": 7777, "queryport": 27015})

    assert mod.get_query_address(server) == expected
    assert mod.get_info_address(server) == expected


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_once_with(server, "\003")


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


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
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
