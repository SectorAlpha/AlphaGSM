"""Full coverage tests for trackmaniaserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.trackmaniaserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.trackmaniaserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=5000, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip")
    assert server.data['port'] == 5000

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 5000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["dedicated_cfg"] = "test"
    server.data["game_settings"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["5001", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "TrackmaniaServer"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.install(server)

def test_sync_server_config_updates_xmlrpc_port(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 5123
    cfg_dir = tmp_path / "GameData" / "Config"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "dedicated_cfg.txt"
    cfg_path.write_text("<dedicated><system_config><xmlrpc_port>5000</xmlrpc_port></system_config></dedicated>")

    mod.sync_server_config(server)

    assert "<xmlrpc_port>5123</xmlrpc_port>" in cfg_path.read_text()

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "TrackmaniaServer"
    (tmp_path / "TrackmaniaServer").write_text("")
    server.data["dedicated_cfg"] = "test"
    server.data["game_settings"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd[-2:] == ["/nodaemon", "/noautoquit"]
    assert cwd == server.data["dir"]

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["dedicated_cfg"] = "test"
    server.data["game_settings"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)

def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()

def test_status():
    server = DummyServer()
    mod.status(server, verbose=True)

def test_query_and_info_addresses():
    server = DummyServer()
    server.data["port"] = 5000
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 5000, "tcp")
        assert mod.get_info_address(server) == ("127.0.0.1", 5000, "tcp")

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

def test_checkvalue_url():
    server = DummyServer()
    result = mod.checkvalue(server, ("url",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_download_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("download_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_dedicated_cfg():
    server = DummyServer()
    result = mod.checkvalue(server, ("dedicated_cfg",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_game_settings():
    server = DummyServer()
    result = mod.checkvalue(server, ("game_settings",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
