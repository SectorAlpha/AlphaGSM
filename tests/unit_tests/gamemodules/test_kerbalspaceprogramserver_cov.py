"""Full coverage tests for kerbalspaceprogramserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.kerbalspaceprogramserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.archive_install': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.github_releases': MagicMock()}):
    import gamemodules.kerbalspaceprogramserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()

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
    mod.configure(server, ask=False, port=8800, dir=str(tmp_path), url="https://example.com/test.zip", download_name="test.zip", version="1.0")
    assert server.data['port'] == 8800

def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8800
    server.data["dir"] = str(tmp_path) + "/"
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    server.data["servername"] = "test"
    server.data["version"] = "test"
    mod.configure(server, ask=True)

def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8801", str(tmp_path / 'custom'), "https://example.com/new.tar.gz"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    server.data["url"] = "https://example.com/test.zip"
    server.data["download_name"] = "test.zip"
    mod.configure(server, ask=True)

def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "LMPServer-linux-x64/Server"
    server.data["url"] = "https://example.com/LunaMultiplayer-Server-linux-x64-Release.zip"
    server.data["download_name"] = "LunaMultiplayer-Server-linux-x64-Release.zip"
    server.data["version"] = "test"
    mod.install(server)

def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "LMPServer-linux-x64/Server"
    exe = tmp_path / "LMPServer-linux-x64" / "Server"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == ["./LMPServer-linux-x64/Server", "--port", "27015"]
    assert cwd == server.data["dir"]
    assert os.access(exe, os.X_OK)


def test_sync_server_config_updates_connection_and_general_settings(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 52176
    server.data["servername"] = "AlphaGSM Kerbal"
    server.data["maxplayers"] = 12

    config_dir = tmp_path / "LMPServer-linux-x64" / "Config"
    config_dir.mkdir(parents=True)
    (config_dir / "ConnectionSettings.xml").write_text(
        """<?xml version="1.0" encoding="utf-16"?>
<ConnectionSettingsDefinition>
  <Port>8800</Port>
</ConnectionSettingsDefinition>""",
        encoding="utf-16",
    )
    (config_dir / "GeneralSettings.xml").write_text(
        """<?xml version="1.0" encoding="utf-16"?>
<GeneralSettingsDefinition>
  <ServerName>Luna Server</ServerName>
  <MaxPlayers>20</MaxPlayers>
</GeneralSettingsDefinition>""",
        encoding="utf-16",
    )

    mod.sync_server_config(server)

    connection_text = (config_dir / "ConnectionSettings.xml").read_text(encoding="utf-16")
    general_text = (config_dir / "GeneralSettings.xml").read_text(encoding="utf-16")
    assert "<Port>52176</Port>" in connection_text
    assert "<ServerName>AlphaGSM Kerbal</ServerName>" in general_text
    assert "<MaxPlayers>12</MaxPlayers>" in general_text


def test_sync_server_config_creates_missing_files_with_managed_values(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 52176
    server.data["servername"] = "AlphaGSM Kerbal"
    server.data["maxplayers"] = 12

    mod.sync_server_config(server)

    config_dir = tmp_path / "LMPServer-linux-x64" / "Config"
    connection_text = (config_dir / "ConnectionSettings.xml").read_text(encoding="utf-16")
    general_text = (config_dir / "GeneralSettings.xml").read_text(encoding="utf-16")
    assert "<Port>52176</Port>" in connection_text
    assert "<ServerName>AlphaGSM Kerbal</ServerName>" in general_text
    assert "<MaxPlayers>12</MaxPlayers>" in general_text


def test_get_query_and_info_address_use_udp_port():
    server = DummyServer()
    server.data["port"] = 52176

    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        expected = ("127.0.0.1", 52176, "udp")
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected

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

def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12")
    assert result == 12

def test_checkvalue_version():
    server = DummyServer()
    result = mod.checkvalue(server, ("version",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dotnetpath():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("dotnetpath",), "/usr/bin/dotnet")


def test_runtime_requirements_no_longer_declare_dotnet_dependency(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LMPServer-linux-x64/Server",
            "port": 8800,
        }
    )
    exe = tmp_path / "LMPServer-linux-x64" / "Server"
    exe.parent.mkdir(parents=True)
    exe.write_text("")

    requirements = mod.get_runtime_requirements(server)

    assert requirements["family"] == "steamcmd-linux"
    assert not requirements.get("host_dependencies")


def test_container_spec_uses_native_start_command(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "LMPServer-linux-x64/Server",
            "port": 8800,
        }
    )
    exe = tmp_path / "LMPServer-linux-x64" / "Server"
    exe.parent.mkdir(parents=True)
    exe.write_text("")

    spec = mod.get_container_spec(server)

    assert spec["command"] == ["./LMPServer-linux-x64/Server", "--port", "8800"]

def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
