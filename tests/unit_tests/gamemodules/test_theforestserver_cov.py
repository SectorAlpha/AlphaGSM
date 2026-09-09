"""Full coverage tests for theforestserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.theforestserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.theforestserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015
    assert int(server.data['steamport']) == 8766
    assert int(server.data['queryport']) == 27016


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8766
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8767", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "TheForestDedicatedServer.exe"
    server.data["Steam_AppID"] = 556450
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 556450
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 556450
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 556450
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
    server.data["exe_name"] = "TheForestDedicatedServer.exe"
    (tmp_path / "TheForestDedicatedServer.exe").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "TheForestDedicatedServer.exe",
        "-batchmode",
        "-nosteamclient",
        "-nographics",
        "-configfilepath",
        "./server-data/Server.cfg",
        "-savefolderpath",
        "./server-data/saves",
    ]
    assert cwd == server.data["dir"]


def test_sync_server_config_writes_required_native_paths_and_ports(tmp_path):
    server = DummyServer("forest")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 28015,
            "queryport": 28016,
            "steamport": 28017,
            "servername": "AlphaGSM forest",
            "maxplayers": 8,
        }
    )

    mod.sync_server_config(server)

    config_path = tmp_path / "server-data" / "Server.cfg"
    config_text = config_path.read_text(encoding="utf-8")
    assert "serverIP 0.0.0.0:28015" in config_text
    assert "serverGamePort 28015" in config_text
    assert "serverQueryPort 28016" in config_text
    assert "serverSteamPort 28017" in config_text
    assert "serverName AlphaGSM forest" in config_text
    assert (tmp_path / "server-data" / "saves").is_dir()


def test_query_and_runtime_contract_use_managed_ports(monkeypatch, tmp_path):
    monkeypatch.setattr(
        mod.runtime_module,
        "resolve_query_host",
        MagicMock(return_value="172.18.0.5"),
    )
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 28015,
            "queryport": 28016,
            "steamport": 28017,
        }
    )

    assert mod.get_query_address(server) == ("172.18.0.5", 28016, "a2s")
    assert mod.get_info_address(server) == ("172.18.0.5", 28016, "a2s")
    requirements = mod.get_runtime_requirements(server)
    assert {
        (entry["host"], entry["protocol"])
        for entry in requirements["ports"]
    } >= {(28015, "udp"), (28016, "udp"), (28017, "udp")}
    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
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
