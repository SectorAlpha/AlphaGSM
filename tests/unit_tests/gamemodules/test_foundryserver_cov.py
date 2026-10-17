"""Full coverage tests for foundryserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.foundryserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.foundryserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=37200, dir=str(tmp_path))
    assert server.data['port'] == 37200


def test_configure_sets_documented_query_port(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_port_is_bindable", lambda port: True)
    server = DummyServer()
    mod.configure(server, ask=False, port=37200, dir=str(tmp_path))
    assert int(server.data["queryport"]) == 27015


def test_configure_moves_query_port_when_default_is_busy(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "_port_is_bindable", lambda port: int(port) != 27015)
    server = DummyServer()
    mod.configure(server, ask=False, port=37200, dir=str(tmp_path))
    assert int(server.data["queryport"]) == 27016
    assert int(server.data["queryport"]) != int(server.data["port"])


def test_sync_server_config_enables_public_a2s_query(tmp_path):
    server = DummyServer("foundry")
    server.data.update({
        "dir": str(tmp_path) + "/",
        "port": 37200,
        "queryport": 27015,
        "servername": "AlphaGSM foundry",
        "worldname": "foundry",
    })
    (tmp_path / "app.cfg").write_text(
        "# keep me\nserver_password=only_friends\nserver_is_public=false\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    text = (tmp_path / "app.cfg").read_text(encoding="utf-8")
    assert text.startswith("# keep me\n")
    values = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    assert values["server_is_public"] == "true"
    assert values["server_query_port"] == "27015"
    assert values["server_port"] == "37200"
    assert values["server_name"] == "AlphaGSM foundry"
    assert values["server_world_name"] == "foundry"
    assert values["server_password"] == "only_friends"
    assert "queryport" in mod.config_sync_keys


def test_prestart_writes_public_query_config(tmp_path):
    server = DummyServer("foundry")
    server.data.update({
        "dir": str(tmp_path) + "/",
        "port": 3724,
        "queryport": 27016,
        "servername": "AlphaGSM foundry",
        "worldname": "world",
    })
    mod.prestart(server)
    text = (tmp_path / "app.cfg").read_text(encoding="utf-8")
    assert "server_is_public=true" in text
    assert "server_query_port=27016" in text


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 37200
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["servername"] = "test"
    server.data["worldname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["37201", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "FoundryDedicatedServer"
    server.data["Steam_AppID"] = 2915550
    server.data["Steam_anonymous_login_possible"] = True
    (tmp_path / "FoundryDedicatedServer").write_text("")
    mod.install(server)


def test_install_without_staged_tree_requires_byo(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "FoundryDedicatedServer"
    server.data["Steam_AppID"] = 2915550
    server.data["Steam_anonymous_login_possible"] = True
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\): foundryserver"):
        mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2915550
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2915550
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2915550
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_query_address_uses_query_port_not_game_port(monkeypatch):
    server = DummyServer()
    server.data["port"] = 37200
    server.data["queryport"] = 27015
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.8")
    assert mod.get_query_address(server) == ("10.0.0.8", 27015, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.8", 27015, "a2s")


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "FoundryDedicatedServer"
    (tmp_path / "FoundryDedicatedServer").write_text("")
    server.data["port"] = 27015
    server.data["servername"] = "test"
    server.data["worldname"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_linux_windows_exe_starts_under_wine(tmp_path, monkeypatch):
    if not mod.IS_LINUX:
        pytest.skip("Wine wrap is Linux-only")
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "FoundryDedicatedServer.exe"
    server.data["wineprefix"] = str(tmp_path / "wineprefix")
    server.data["port"] = 37200
    server.data["servername"] = "AlphaGSM foundry"
    server.data["worldname"] = "foundry"
    (tmp_path / "FoundryDedicatedServer.exe").write_text("")
    monkeypatch.setattr(
        mod.proton,
        "wrap_xvfb_command",
        lambda command, wineprefix=None, prefer_proton=False: ["xvfb-run", *command],
    )
    cmd, cwd = mod.get_start_command(server)
    assert cmd[0] == "env"
    assert "SteamAppId=983870" in cmd
    assert "xvfb-run" in cmd
    assert "./FoundryDedicatedServer.exe" in cmd
    assert "--port" in cmd
    assert cwd == server.data["dir"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["servername"] = "test"
    server.data["worldname"] = "test"
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\): foundryserver"):
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


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "/test/value")
    assert result == "/test/value"


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
