"""Full coverage tests for gravserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.gravserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.gravserver as mod
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
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["peerport"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "CAGGameServer-Win32-Shipping"
    (tmp_path / "CAGGameServer-Win32-Shipping").write_text("")
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["peerport"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["adminpassword"] = "test"
    server.data["maxplayers"] = 27015
    server.data["peerport"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
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


def test_checkvalue_peerport():
    server = DummyServer()
    result = mod.checkvalue(server, ("peerport",), "12345")
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


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")

