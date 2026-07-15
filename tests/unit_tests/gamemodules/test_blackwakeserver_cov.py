"""Full coverage tests for blackwakeserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.blackwakeserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.blackwakeserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data["gamemode"] == mod.DEFAULT_GAMEMODE
    assert server.data["servername"] == server.name
    assert server.data["serverpassword"] == mod.DEFAULT_SERVER_PASSWORD


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


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Blackwake Dedicated Server.exe"
    server.data["Steam_AppID"] = 423410
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 423410
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 423410
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 423410
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
    server.data["exe_name"] = "Blackwake Dedicated Server.exe"
    (tmp_path / "Blackwake Dedicated Server.exe").write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_query_and_info_address_use_queryport_for_process_runtime():
    server = DummyServer(name="blackwake-it")
    server.data.update({"queryport": 27016, "runtime": "process"})

    assert mod.get_query_address(server) == ("127.0.0.1", 27016, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.1", 27016, "a2s")


def test_query_and_info_address_use_tcp_main_port_for_docker_runtime():
    server = DummyServer(name="blackwake-it")
    server.data.update({"port": 34238, "queryport": 27016, "runtime": "docker"})

    assert mod.get_query_address(server) == ("127.0.0.1", 34238, "tcp")
    assert mod.get_info_address(server) == ("127.0.0.1", 34238, "tcp")


def test_sync_server_config_updates_server_cfg(tmp_path):
    server = DummyServer(name="blackwake-it")
    server.data.update({
        "dir": str(tmp_path),
        "port": 34238,
        "queryport": 27016,
        "servername": "AlphaGSM Blackwake",
        "serverpassword": "alphagsm123",
        "gamemode": 7,
    })
    cfg_path = tmp_path / "Server.cfg"
    cfg_path.write_text(
        "serverName=my server\n"
        "port=25001\n"
        "sport=27015\n"
        "password=\n"
        "useBots=1\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert cfg_path.read_text(encoding="utf-8").splitlines() == [
        "serverName=AlphaGSM Blackwake",
        "port=34238",
        "sport=27016",
        "password=alphagsm123",
        "useBots=0",
        "gamemode=7",
    ]


def test_checkvalue_serverpassword_requires_min_length():
    server = DummyServer()

    with pytest.raises(ServerError, match="at least 4 characters"):
        mod.checkvalue(server, ("serverpassword",), "abc")

    assert mod.checkvalue(server, ("serverpassword",), "alphagsm123") == "alphagsm123"


def test_checkvalue_gamemode_range():
    server = DummyServer()

    with pytest.raises(ServerError, match="between 1 and 8"):
        mod.checkvalue(server, ("gamemode",), "9")

    assert mod.checkvalue(server, ("gamemode",), "7") == 7


def test_wrap_linux_command_uses_xvfb_when_available(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/xvfb-run" if name == "xvfb-run" else None)
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "wine",
            *cmd,
        ],
    )
    monkeypatch.setattr(
        mod.proton,
        "prepend_env_assignments",
        lambda cmd, **env: (
            [cmd[0], *(f"{key}={value}" for key, value in env.items()), *cmd[1:]]
            if cmd and cmd[0] == "env"
            else ["env", *(f"{key}={value}" for key, value in env.items()), *cmd]
        ),
    )

    wrapped = mod._wrap_linux_command(["BlackwakeServer.exe", "-batchmode"])

    assert wrapped == [
        "xvfb-run",
        "-a",
        "env",
        "SDL_VIDEODRIVER=x11",
        "SDL_AUDIODRIVER=dummy",
        "wine",
        "BlackwakeServer.exe",
        "-batchmode",
    ]


def test_wrap_linux_command_does_not_force_proton(monkeypatch):
    seen = {}

    monkeypatch.setattr(mod.shutil, "which", lambda name: None)

    def fake_wrap(cmd, wineprefix=None, prefer_proton=False):
        seen["prefer_proton"] = prefer_proton
        return ["env", "wine", *cmd]

    monkeypatch.setattr(mod.proton, "wrap_command", fake_wrap)

    wrapped = mod._wrap_linux_command(["BlackwakeServer.exe", "-batchmode"])

    assert wrapped == ["env", "wine", "BlackwakeServer.exe", "-batchmode"]
    assert seen["prefer_proton"] is False


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
    sender = MagicMock()
    original = mod.runtime_module.send_to_server
    mod.runtime_module.send_to_server = sender
    try:
        mod.do_stop(server, 0)
    finally:
        mod.runtime_module.send_to_server = original
    sender.assert_called_once_with(server, "\003")


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
