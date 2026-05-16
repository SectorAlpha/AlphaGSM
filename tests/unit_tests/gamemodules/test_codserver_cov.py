"""Full coverage tests for codserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.codserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.codserver as mod
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
    mod.configure(server, ask=False, port=28960, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip")
    assert server.data['port'] == 28960

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 28960
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["28961", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod_lnxded"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.install(server)

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "cod_lnxded"
    (tmp_path / "cod_lnxded").write_text("")
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./cod_lnxded",
        "+set",
        "fs_game",
        "test",
        "+set",
        "sv_hostname",
        "test",
        "+set",
        "net_port",
        "27015",
        "+map",
        "test",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_cod_launch_tokens():
    assert mod.setting_schema["fs_game"].canonical_key == "moddir"
    assert mod.setting_schema["fs_game"].launch_arg_tokens == ("+set", "fs_game")
    assert mod.setting_schema["hostname"].launch_arg_tokens == ("+set", "sv_hostname")
    assert mod.setting_schema["port"].launch_arg_tokens == ("+set", "net_port")


def test_sync_server_config_updates_mod_server_cfg(tmp_path):
    server = DummyServer("cod")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "moddir": "main",
            "hostname": "AlphaGSM cod",
            "startmap": "mp_harbor",
        }
    )
    cfg_dir = tmp_path / "main"
    cfg_dir.mkdir(parents=True)
    cfg_path = cfg_dir / "server.cfg"
    cfg_path.write_text(
        'hostname="Old Name"\nmoddir=uo\nstartmap=mp_carentan\nset scr_friendlyfire 1\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert cfg_path.read_text(encoding="utf-8") == (
        'hostname="AlphaGSM cod"\n'
        'moddir=main\n'
        'startmap=mp_harbor\n'
        'set scr_friendlyfire 1\n'
    )

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["hostname"] = "test"
    server.data["moddir"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
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

def test_checkvalue_moddir():
    server = DummyServer()
    result = mod.checkvalue(server, ("moddir",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")

