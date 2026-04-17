"""Full coverage tests for rimworldtogetherserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.rimworldtogetherserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.github_releases': MagicMock()}):
    import gamemodules.rimworldtogetherserver as mod
    from server import ServerError

class DummyData(dict):
    def save(self):
        pass
    def setdefault(self, key, value=None):
        if key not in self:
            self[key] = value
        return self[key]
    def get(self, key, default=None):
        return super().get(key, default)

class DummyServer:
    def __init__(self, name="testserver"):
        self.name = name
        self.data = DummyData()
        self._stopped = False
        self._started = False
    def stop(self):
        self._stopped = True
    def start(self):
        self._started = True

def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=25555, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip", version="1.0")
    assert server.data['port'] == 25555

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 25555
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["25556", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "RimworldTogetherServer.x86_64"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    server.data["port"] = 25555
    mod.install(server)
    assert (tmp_path / "Config" / "ServerSettings.json").read_text() == '{\n  "Port": 25555\n}\n'
    assert (tmp_path / "Configs" / "ServerConfig.json").read_text() == '{\n  "Port": 25555\n}\n'


def test_install_preserves_existing_server_config_fields(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "RimworldTogetherServer.x86_64"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    server.data["port"] = 25556
    configs_dir = tmp_path / "Configs"
    configs_dir.mkdir(parents=True)
    (configs_dir / "ServerConfig.json").write_text('{"Name":"Test","Port":25555}\n')

    mod.install(server)

    assert (configs_dir / "ServerConfig.json").read_text() == '{\n  "Name": "Test",\n  "Port": 25556\n}\n'


def test_setting_schema_exposes_verified_port_only():
    schema = mod.setting_schema

    assert schema["port"].canonical_key == "port"
    assert schema["port"].aliases == ("gameport",)
    assert schema["port"].storage_key is None
    assert schema["port"].apply_to == ("datastore", "native_config", "launch_args")
    assert mod.config_sync_keys == ("port",)
    assert mod.list_setting_values(DummyServer(), "port") is None


def test_sync_server_config_updates_both_config_locations(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 25557
    config_dir = tmp_path / "Config"
    live_config_dir = tmp_path / "Configs"
    config_dir.mkdir(parents=True)
    live_config_dir.mkdir(parents=True)
    (config_dir / "ServerSettings.json").write_text('{"Port":25555}\n')
    (live_config_dir / "ServerConfig.json").write_text('{"Port":25555,"Name":"Test"}\n')

    mod.sync_server_config(server)

    assert (config_dir / "ServerSettings.json").read_text() == '{\n  "Port": 25557\n}\n'
    assert (live_config_dir / "ServerConfig.json").read_text() == '{\n  "Port": 25557,\n  "Name": "Test"\n}\n'

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "RimworldTogetherServer.x86_64"
    (tmp_path / "RimworldTogetherServer.x86_64").write_text("")
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)

def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.screen.send_to_server.assert_called()

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

def test_checkvalue_version():
    server = DummyServer()
    result = mod.checkvalue(server, ("version",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
