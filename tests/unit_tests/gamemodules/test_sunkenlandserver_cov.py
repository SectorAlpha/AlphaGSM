"""Full coverage tests for sunkenlandserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.sunkenlandserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.sunkenlandserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=29000, dir=str(tmp_path))
    assert server.data['port'] == 29000


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 29000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["29001", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Sunkenland-DedicatedServer.exe"
    server.data["Steam_AppID"] = 2667530
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2667530
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2667530
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2667530
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
    server.data["exe_name"] = "Sunkenland-DedicatedServer.exe"
    (tmp_path / "Sunkenland-DedicatedServer.exe").write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


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


@pytest.mark.parametrize("value", ["DISPLAY=secret", "WINEDLLOVERRIDES=literal"])
def test_linux_launch_enables_virtual_display(tmp_path, monkeypatch, value):
    import importlib
    real_proton = importlib.import_module("utils.proton")
    monkeypatch.setattr(mod, "IS_LINUX", True)
    monkeypatch.setattr(mod.proton, "prepend_env_assignments", real_proton.prepend_env_assignments)
    monkeypatch.setenv("WINEDLLOVERRIDES", "winex11.drv=")
    monkeypatch.setenv("SDL_VIDEODRIVER", "offscreen")
    monkeypatch.setattr(mod.proton, "wrap_command", lambda command, **kwargs: [
        "env", "DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=", "wine", *command,
    ])
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    (tmp_path / server.data["exe_name"]).touch()
    server.data["servername"] = value

    command, _cwd = mod.get_start_command(server)

    assert command[:2] == ["xvfb-run", "-a"]
    assert "DISPLAY=" not in command
    assert "WINEDLLOVERRIDES=" in command
    assert "SDL_VIDEODRIVER=x11" in command
    assert "SDL_AUDIODRIVER=dummy" in command
    assert "WINEDLLOVERRIDES=winex11.drv=" not in command
    assert server.data["exe_name"] in command
    assert command.count(value) == 1


def test_docker_runtime_enables_virtual_display():
    server = DummyServer()
    requirements = mod.get_runtime_requirements(server)

    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["WINEDLLOVERRIDES"] == ""


def test_query_and_info_use_managed_tcp_port(monkeypatch):
    monkeypatch.setattr(
        mod.runtime_module,
        "resolve_query_host",
        MagicMock(return_value="172.18.0.5"),
    )
    server = DummyServer()
    server.data["port"] = 28015

    assert mod.get_query_address(server) == ("172.18.0.5", 28015, "tcp")
    assert mod.get_info_address(server) == ("172.18.0.5", 28015, "tcp")
