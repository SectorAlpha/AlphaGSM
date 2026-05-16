"""Full coverage tests for mumbleserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.mumbleserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.mumbleserver as mod
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
    mod.configure(server, ask=False, port=64738, dir=str(tmp_path))
    assert server.data['port'] == 64738


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 64738
    server.data["dir"] = str(tmp_path) + "/"
    server.data["database"] = "test"
    server.data["serverpassword"] = "test"
    server.data["users"] = "test"
    server.data["welcometext"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["64739", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "server"
    server.data["port"] = 64738
    server.data["welcometext"] = "Welcome"
    server.data["serverpassword"] = ""
    server.data["users"] = 10
    server.data["database"] = str(tmp_path / "murmur.sqlite")
    mod.install(server)


def test_sync_server_config_rewrites_mumble_config(tmp_path):
    server = DummyServer("voice")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 64739
    server.data["welcometext"] = "Welcome to voice"
    server.data["users"] = "42"
    server.data["database"] = "voice.sqlite"
    server.data["serverpassword"] = "secret"

    mod.sync_server_config(server)

    config_text = (tmp_path / "mumble-server.ini").read_text()
    assert "welcometext=Welcome to voice" in config_text
    assert "port=64739" in config_text
    assert "users=42" in config_text
    assert "database=voice.sqlite" in config_text
    assert "serverpassword=secret" in config_text


def test_setting_schema_exposes_canonical_ini_keys():
    schema = mod.setting_schema

    assert mod.config_sync_keys == ("port", "users", "database", "serverpassword", "welcometext")
    assert schema["maxplayers"].storage_key == "users"
    assert schema["maxplayers"].native_config_key == "users"
    assert schema["serverpassword"].secret is True
    assert schema["maxplayers"].value_type == "integer"


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "server"
    (tmp_path / "server").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_query_and_info_address_use_runtime_query_host():
    server = DummyServer()
    server.data["port"] = 64738
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="172.18.0.25") as resolver:
        assert mod.get_query_address(server) == ("172.18.0.25", 64738, "tcp")
        assert mod.get_info_address(server) == ("172.18.0.25", 64738, "tcp")
        assert resolver.call_count == 2


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


def test_checkvalue_welcometext():
    server = DummyServer()
    result = mod.checkvalue(server, ("welcometext",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_users():
    server = DummyServer()
    result = mod.checkvalue(server, ("users",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_database():
    server = DummyServer()
    result = mod.checkvalue(server, ("database",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "/test/value")
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
