"""Full coverage tests for starbound."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.starbound', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.starbound as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_setup_command_accepts_port_then_dir():
    names = [spec.name for spec in mod.command_args["setup"].optionalarguments]
    assert names[:2] == ["PORT", "DIR"]


def test_recipe_declares_one_authenticated_steamcmd_source():
    server = DummyServer()
    recipe = mod.get_asset_requirements(server)
    steam_sources = [source for source in recipe["sources"] if source["kind"] == "steamcmd"]
    assert [source["kind"] for source in recipe["sources"]] == ["operator-files", "steamcmd"]
    assert len(steam_sources) == 1
    source = steam_sources[0]
    assert source["app_id"] == 211820
    assert source["authentication"] == "required"
    assert source["platform"] == "linux"
    assert "linux64/starbound_server" in recipe["include"]
    assert "assets/packed.pak" in recipe["include"]
    assert "win64/starbound_server.exe" not in recipe["include"]


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data["Steam_AppID"] == 211820
    assert server.data["backupfiles"] == ["giraffe_storage", "linux64/sbboot.config"]
    assert server.data["exe_name"] == "linux64/starbound_server"
    assert server.data["port"] == 27015


def test_configure_defaults_to_documented_game_port(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, dir=str(tmp_path))
    assert server.data["port"] == 21025


def test_sync_server_config_enables_a2s_query_server(tmp_path):
    import json

    server = DummyServer("sb")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 21025
    config_path = tmp_path / "storage" / "starbound_server.config"
    config_path.parent.mkdir()
    config_path.write_text(json.dumps({
        "runQueryServer": False,
        "queryServerPort": 1,
        "gameServerPort": 1,
        "maxPlayers": 4,
        "serverUsers": {"admin": {"admin": True, "password": "secret"}},
    }), encoding="utf-8")

    mod.sync_server_config(server)

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["runQueryServer"] is True
    assert payload["queryServerPort"] == 21025
    assert payload["gameServerPort"] == 21025
    assert payload["maxPlayers"] == 4
    assert payload["serverUsers"]["admin"]["password"] == "secret"
    assert "port" in mod.config_sync_keys


def test_prestart_writes_query_server_config(tmp_path):
    import json

    server = DummyServer("sb")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 21025
    mod.prestart(server)
    payload = json.loads((tmp_path / "storage" / "starbound_server.config").read_text(encoding="utf-8"))
    assert payload["runQueryServer"] is True
    assert payload["queryServerPort"] == 21025
    assert payload["gameServerPort"] == 21025


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["21030", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)
    assert server.data["port"] == 21030


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "linux64/starbound_server"
    server.data["Steam_AppID"] = 211820
    server.data["Steam_anonymous_login_possible"] = True
    exe_path = tmp_path / "linux64/starbound_server"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    mod.steamcmd.download = MagicMock()
    mod.install(server)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 211820, True
    )
    assert server.data["exe_name"] == "linux64/starbound_server"


def test_install_passes_saved_steam_auth_profile(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "linux64/starbound_server"
    server.data["steam_auth_profile"] = "owned"
    exe_path = tmp_path / "linux64/starbound_server"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("server")
    mod.steamcmd.download = MagicMock()
    mod.install(server)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 211820, True, auth_profile="owned"
    )


def test_install_selects_linux_binary_when_linux64_is_absent(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "linux64/starbound_server"
    exe_path = tmp_path / "linux/starbound_server"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("server")
    mod.steamcmd.download = MagicMock()
    mod.install(server)
    assert server.data["exe_name"] == "linux/starbound_server"
    assert "auth_profile" not in mod.steamcmd.download.call_args.kwargs


def test_install_without_staged_tree_requires_byo(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "linux64/starbound_server"
    server.data["Steam_AppID"] = 211820
    server.data["Steam_anonymous_login_possible"] = True
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\): starbound"):
        mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 211820
    server.data["Steam_anonymous_login_possible"] = True
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=True, restart=True)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 211820, True, validate=True
    )
    assert server._stopped
    assert server._started


def test_update_passes_saved_steam_auth_profile(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 211820
    server.data["Steam_anonymous_login_possible"] = True
    server.data["steam_auth_profile"] = "owned"
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=False, restart=False)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 211820, True, validate=False, auth_profile="owned"
    )


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 211820
    server.data["Steam_anonymous_login_possible"] = True
    mod.steamcmd.download = MagicMock()
    mod.update(server, validate=False, restart=False)
    mod.steamcmd.download.assert_called_once_with(
        str(tmp_path) + "/", 211820, True, validate=False
    )
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 211820
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_query_address_uses_game_port(monkeypatch):
    server = DummyServer()
    server.data["port"] = 21025
    server.data["queryport"] = 27015
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.1.2.3")
    assert mod.get_query_address(server) == ("10.1.2.3", 21025, "a2s")
    assert mod.get_info_address(server) == ("10.1.2.3", 21025, "a2s")


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "linux64/starbound_server"
    exe_path = tmp_path / "linux64/starbound_server"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert cmd == ["./starbound_server"]
    assert cwd == str(tmp_path / "linux64")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError, match="ENABLED \\(BYO\\): starbound"):
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
        mod.checkvalue(server, ("exe_name",))


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
