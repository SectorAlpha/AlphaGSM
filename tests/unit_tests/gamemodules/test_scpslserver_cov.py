"""Full coverage tests for scpslserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.scpslserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.scpslserver as mod
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
    assert server.data['exe_name'] == 'LocalAdmin'
    assert server.data['queryport'] == 7778


def test_configure_custom_queryport_follows_port(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=9000, dir=str(tmp_path / 'install'))
    assert server.data['port'] == 9000
    assert server.data['queryport'] == 9001


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "LocalAdmin"
    server.data["Steam_AppID"] = 996560
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 7777
    server.data["queryport"] = 7778
    server.data["contactemail"] = ""
    (tmp_path / "SCPSL.x86_64").write_text("")
    (tmp_path / "LocalAdmin").write_text("")
    mod.install(server)
    assert (tmp_path / "home/.config/SCP Secret Laboratory/config/localadmin_internal_data.json").is_file()
    gameplay = (tmp_path / "home/.config/SCP Secret Laboratory/config/7777/config_gameplay.txt").read_text()
    assert "enable_query: true" in gameplay
    assert "contact_email: default" in gameplay
    assert "query_administrator_password: alphagsmquery" in gameplay


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 996560
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 996560
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 996560
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
    server.data["exe_name"] = "LocalAdmin"
    (tmp_path / "LocalAdmin").write_text("")
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    server.data["contactemail"] = "ops@example.com"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "env",
        "HOME=" + str(tmp_path / "home"),
        "XDG_CONFIG_HOME=" + str(tmp_path / "home/.config"),
        "./LocalAdmin",
        "27015",
    ]
    assert cwd == str(tmp_path) + "/"
    gameplay = (tmp_path / "home/.config/SCP Secret Laboratory/config/27015/config_gameplay.txt").read_text()
    assert "enable_query: true" in gameplay
    assert "contact_email: ops@example.com" in gameplay
    assert "query_administrator_password: alphagsmquery" in gameplay


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_query_address():
    server = DummyServer()
    server.data["queryport"] = 7778
    assert mod.get_query_address(server) == ("127.0.0.1", 7778, "tcp")


def test_get_info_address():
    server = DummyServer()
    server.data["queryport"] = 7778
    assert mod.get_info_address(server) == ("127.0.0.1", 7778, "tcp")


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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_contactemail():
    server = DummyServer()
    result = mod.checkvalue(server, ("contactemail",), "ops@example.com")
    assert result == "ops@example.com"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")

