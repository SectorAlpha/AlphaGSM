"""Full coverage tests for abfserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
sys.modules.pop('gamemodules.abfserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.abfserver as mod
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
    server.data["queryport"] = 27015
    server.data["world"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe"
    server.data["Steam_AppID"] = 2857200
    server.data["Steam_anonymous_login_possible"] = True
    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)
    download.assert_called_once_with(
        server.data["dir"], 2857200, True, validate=False, force_windows=True
    )


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2857200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2857200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2857200
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
    server_module = mod
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe"
    exe_path = tmp_path / server.data["exe_name"]
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["world"] = "test"
    with patch.object(server_module, "IS_LINUX", False):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe",
        "-log",
        "-newconsole",
        "-useperfthreads",
        "-NoAsyncLoadingThread",
        "-WorldSaveName=test",
        "-Port=27015",
        "-QueryPort=27015",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_wraps_windows_server_for_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    server = DummyServer()
    server.data.update({
        "dir": str(tmp_path) + "/",
        "exe_name": "AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe",
        "port": 7777,
        "queryport": 27016,
        "world": "test",
        "wineprefix": "/srv/abf-prefix",
    })
    exe_path = tmp_path / server.data["exe_name"]
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")

    with patch.object(mod.proton, "wrap_command", side_effect=lambda command, **_kwargs: command) as wrap_command:
        mod.get_start_command(server)

    wrap_command.assert_called_once_with(
        [
            "AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe",
            "-log",
            "-newconsole",
            "-useperfthreads",
            "-NoAsyncLoadingThread",
            "-WorldSaveName=test",
            "-Port=7777",
            "-QueryPort=27016",
        ],
        wineprefix="/srv/abf-prefix",
        prefer_proton=True,
    )


def test_runtime_contract_uses_shared_wine_proton_builder():
    server = DummyServer()
    server.data.update({"dir": "/srv/abf/", "port": 7777, "queryport": 27016})

    requirements = mod.get_runtime_requirements(server)

    assert requirements["family"] == "wine-proton"
    assert {port["host"] for port in requirements["ports"]} == {7777, 27016}


def test_container_spec_publishes_game_and_query_ports(tmp_path):
    server = DummyServer()
    server.data.update({
        "dir": str(tmp_path) + "/",
        "exe_name": "AbioticFactor/Binaries/Win64/AbioticFactorServer-Win64-Shipping.exe",
        "port": 7777,
        "queryport": 27016,
        "world": "test",
    })
    exe_path = tmp_path / server.data["exe_name"]
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")

    with patch.object(mod.proton, "wrap_command", side_effect=lambda command, **_kwargs: command):
        spec = mod.get_container_spec(server)

    assert spec["ports"]
    assert {port["host"] for port in spec["ports"]} == {7777, 27016}
    assert "AbioticFactorServer-Win64-Shipping.exe" in " ".join(spec["command"])


def test_setting_schema_exposes_abioticfactor_launch_formats():
    assert mod.setting_schema["world"].launch_arg_format == "-WorldSaveName={value}"
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["world"] = "test"
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


def test_checkvalue_world():
    server = DummyServer()
    result = mod.checkvalue(server, ("world",), "/test/value")
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
