"""Full coverage tests for saleblazersserver."""

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.saleblazersserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.saleblazersserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=34567, dir=str(tmp_path))
    assert server.data['port'] == 34567
    assert server.data["queryport"] == "34568"
    assert server.data["maxplayers"] == "8"
    assert server.data["servername"] == server.name
    assert server.data["serverpassword"] == ""


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Default/Saleblazers.exe"
    server.data["Steam_AppID"] = 3099600
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3099600
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3099600
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 3099600
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
    server.data["exe_name"] = "Default/Saleblazers.exe"
    exe_path = tmp_path / "Default/Saleblazers.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "Saleblazers.exe",
        "-headless",
        "-config",
        "../DedicatedServerConfig.json",
        "-batchmode",
        "-nographics",
        "-logFile",
        "../server.log",
    ]
    assert cwd == str(exe_path.parent)


def test_get_start_command_linux_drops_headless_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    monkeypatch.setattr(mod, "_wrap_linux_command", lambda cmd, wineprefix=None: list(cmd))
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Default/Saleblazers.exe"
    exe_path = tmp_path / "Default/Saleblazers.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "Saleblazers.exe",
        "-config",
        "../DedicatedServerConfig.json",
        "-batchmode",
        "-logFile",
        "../server.log",
    ]
    assert cwd == str(exe_path.parent)


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

    wrapped = mod._wrap_linux_command(["Default/Saleblazers.exe", "-batchmode"])

    assert wrapped == [
        "xvfb-run",
        "-a",
        "env",
        "SDL_VIDEODRIVER=x11",
        "SDL_AUDIODRIVER=dummy",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "wine",
        "Default/Saleblazers.exe",
        "-batchmode",
    ]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_sync_server_config_writes_dedicated_server_json(tmp_path):
    server = DummyServer("sale")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": "34567",
            "maxplayers": "12",
            "servername": "AlphaGSM Test",
            "serverpassword": "secret",
        }
    )

    mod.sync_server_config(server)

    config_path = tmp_path / "DedicatedServerConfig.json"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["LoginConfig"]["HostingPort"] == 34567
    options = {
        item["Key"]: item["Value"]
        for item in payload["LobbyConfig"]["SerializedOptions"]["Options"]
    }
    assert options["Lobby_Name"] == "AlphaGSM Test"
    assert options["Lobby_HostName"] == "AlphaGSM Test"
    assert options["Lobby_Password"] == "secret"
    assert options["Lobby_Capacity"] == "12"


def test_prestart_refreshes_dedicated_config(tmp_path):
    server = DummyServer("sale")
    server.data.update({"dir": str(tmp_path) + "/", "port": "27015", "queryport": "99999"})

    mod.prestart(server)

    assert (tmp_path / "DedicatedServerConfig.json").is_file()
    assert server.data["queryport"] == "27016"

def test_query_and_info_address_use_derived_udp_status_port(monkeypatch):
    server = DummyServer("sale")
    server.data["port"] = "38721"
    server.data["queryport"] = "27016"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 38722, "udp")
    assert mod.get_info_address(server) == ("10.0.0.10", 38722, "udp")


def test_runtime_ports_follow_game_port_plus_one(tmp_path):
    server = DummyServer("sale")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = "38721"
    server.data["queryport"] = "27016"

    requirements = mod.get_runtime_requirements(server)
    ports = {(entry["host"], entry["protocol"]) for entry in requirements["ports"]}

    assert (38721, "udp") in ports
    assert (38721, "tcp") in ports
    assert (38722, "udp") in ports
    assert (38722, "tcp") in ports
    assert server.data["queryport"] == "38722"


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
