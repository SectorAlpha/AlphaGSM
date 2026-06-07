"""Full coverage tests for cryofallserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.cryofallserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.cryofallserver as mod
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
    mod.configure(server, ask=False, port=6000, dir=str(tmp_path))
    assert server.data['port'] == 6000


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 6000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["servername"] = "test"
    server.data["maxplayers"] = 100
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["6001", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Server/CryoFall_Server.dll"
    server.data["Steam_AppID"] = 1061710
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1061710
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1061710
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1061710
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Server/CryoFall_Server.dll"
    server.data["dotnetpath"] = "/usr/bin/dotnet"
    exe = tmp_path / "Binaries" / "Server" / "CryoFall_Server.dll"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert cmd == ["/usr/bin/dotnet", "./Binaries/Server/CryoFall_Server.dll", "loadOrNew"]
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_uses_nested_cryofall_install_root(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "CryoFall Dedicated Server"
    exe = nested_root / "Binaries" / "Server" / "CryoFall_Server.dll"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Server/CryoFall_Server.dll"
    server.data["dotnetpath"] = "/usr/bin/dotnet"

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "/usr/bin/dotnet",
        "./CryoFall Dedicated Server/Binaries/Server/CryoFall_Server.dll",
        "loadOrNew",
    ]
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_prefers_nested_cryofall_install_root_over_top_level_file(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "CryoFall Dedicated Server"
    nested_exe = nested_root / "Binaries" / "Server" / "CryoFall_Server.dll"
    nested_exe.parent.mkdir(parents=True)
    nested_exe.write_text("")
    top_level_exe = tmp_path / "Binaries" / "Server" / "CryoFall_Server.dll"
    top_level_exe.parent.mkdir(parents=True)
    top_level_exe.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Server/CryoFall_Server.dll"
    server.data["dotnetpath"] = "/usr/bin/dotnet"

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "/usr/bin/dotnet",
        "./CryoFall Dedicated Server/Binaries/Server/CryoFall_Server.dll",
        "loadOrNew",
    ]
    assert cwd == str(tmp_path) + "/"


def test_sync_server_config(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 6123
    server.data["servername"] = "AlphaGSM Cryo"
    server.data["maxplayers"] = 42
    mod.sync_server_config(server)
    config_path = tmp_path / "Data" / "SettingsServer.xml"
    text = config_path.read_text()
    assert "<port>6123</port>" in text
    assert "<name>AlphaGSM Cryo</name>" in text
    assert "<players_max_count>42</players_max_count>" in text


def test_sync_server_config_uses_nested_cryofall_install_root(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "CryoFall Dedicated Server"
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 6123
    server.data["servername"] = "AlphaGSM Cryo"
    server.data["maxplayers"] = 42
    (nested_root / "Binaries" / "Server").mkdir(parents=True)
    (nested_root / "Binaries" / "Server" / "CryoFall_Server.dll").write_text("")

    mod.sync_server_config(server)

    config_path = nested_root / "Data" / "SettingsServer.xml"
    assert config_path.is_file()


def test_sync_server_config_without_dir_is_noop():
    server = DummyServer()
    server.data["port"] = 6123
    server.data["servername"] = "AlphaGSM Cryo"
    server.data["maxplayers"] = 42
    mod.sync_server_config(server)


def test_get_query_and_info_address():
    server = DummyServer()
    server.data["port"] = 6000
    expected = ("127.0.0.1", 6000, "udp")
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected


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


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "123")
    assert result == 123


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "AlphaGSM Cryo")
    assert result == "AlphaGSM Cryo"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dotnetpath():
    server = DummyServer()
    result = mod.checkvalue(server, ("dotnetpath",), "/usr/bin/dotnet")
    assert result == "/usr/bin/dotnet"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
