"""Full coverage tests for warbandserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.warbandserver', None)
with patch.dict('sys.modules', {'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock()}):
    import gamemodules.warbandserver as mod
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
    mod.configure(server, ask=False, port=7240, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip", version="1.0")
    assert server.data['port'] == 7240
    assert server.data['exe_name'] == mod.WARBAND_DEFAULT_EXE

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7240
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["maxplayers"] = 27015
    server.data["version"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7241", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_configure_resolves_download(tmp_path):
    server = DummyServer()
    with patch.object(mod, 'resolve_download', return_value=('1.174', 'https://example.com/warband.tar.gz')):
        mod.configure(server, ask=False, port=7240, dir=str(tmp_path))
    assert server.data['url'] == 'https://example.com/warband.tar.gz'
    assert server.data['version'] == '1.174'

def test_resolve_download_uses_default_direct_archive():
    version, url = mod.resolve_download()
    assert version == mod.WARBAND_DEFAULT_VERSION
    assert url == "https://download.taleworlds.com/mb_warband_dedicated_1174.zip"

def test_resolve_download_formats_explicit_version_token():
    version, url = mod.resolve_download("1.173")
    assert version == "1.173"
    assert url == "https://download.taleworlds.com/mb_warband_dedicated_1173.zip"

def test_sync_server_config_updates_sample_battle(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 7242
    server.data["maxplayers"] = 48
    config_dir = tmp_path / "Mount&Blade Warband Dedicated"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "Sample_Battle.txt"
    config_path.write_text(
        "set_port 7240\nset_steam_port 7241\nset_max_players 32 32\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    config_text = config_path.read_text(encoding="utf-8")
    assert "set_port 7242" in config_text
    assert "set_steam_port 7243" in config_text
    assert "set_max_players 48 48" in config_text

def test_wrap_linux_command_uses_xvfb_when_available(monkeypatch):
    monkeypatch.setattr(mod.shutil, 'which', lambda name: '/usr/bin/xvfb-run' if name == 'xvfb-run' else None)
    monkeypatch.setattr(
        mod.proton,
        'wrap_command',
        lambda cmd, wineprefix=None: [
            'env',
            'DISPLAY=',
            'WINEDLLOVERRIDES=winex11.drv=',
            'wine',
            *cmd,
        ],
    )

    wrapped = mod._wrap_linux_command(['mb_warband_dedicated.exe'])

    assert wrapped == ['xvfb-run', '-a', 'env', 'wine', 'mb_warband_dedicated.exe']

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mb_warband_dedicated"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["version"] = "test"
    mod.install(server)

def test_install_resolves_download(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "mb_warband_dedicated"
    server.data["download_name"] = "test.tar.gz"
    with patch.object(mod, 'resolve_download', return_value=('1.174', 'https://example.com/warband.tar.gz')):
        mod.install(server)
    assert server.data['url'] == 'https://example.com/warband.tar.gz'

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = mod.WARBAND_DEFAULT_EXE
    exe_path = tmp_path / "Mount&Blade Warband Dedicated" / "mb_warband_dedicated.exe"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    with patch.object(mod, '_wrap_linux_command', side_effect=lambda cmd, **_kwargs: list(cmd)):
        cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cmd == ['mb_warband_dedicated.exe', '-r', 'Sample_Battle.txt', '-m', 'Native']
    assert cwd == str(tmp_path / 'Mount&Blade Warband Dedicated')

def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Mount&Blade Warband Dedicated/nonexistent.exe"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)

def test_do_stop():
    server = DummyServer()
    with patch.object(mod.runtime_module, 'send_to_server') as send_to_server:
        mod.do_stop(server, 0)
    send_to_server.assert_called()

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

def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
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

