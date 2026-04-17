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


def test_configure_defaults_to_shared_servers_path_in_manager_mode(monkeypatch):
    server = DummyServer("scp")

    monkeypatch.setattr(mod.runtime_module, "suggest_install_dir", lambda current_server, current_dir=None: "/shared/servers/" + current_server.name)

    mod.configure(server, ask=False)

    assert server.data["dir"] == "/shared/servers/scp/"


def test_configure_replaces_stale_invalid_manager_path(monkeypatch):
    server = DummyServer("scp")
    server.data["dir"] = "/root/scp/"

    monkeypatch.setattr(mod.runtime_module, "suggest_install_dir", lambda current_server, current_dir=None: "/shared/servers/" + current_server.name)

    mod.configure(server, ask=False)

    assert server.data["dir"] == "/shared/servers/scp/"


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


def test_sync_server_config_updates_contact_email(tmp_path):
    server = DummyServer("scp")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 7777
    server.data["contactemail"] = "ops@example.com"
    server.data["servername"] = "AlphaGSM SCP"
    server.data["queryport"] = 8888
    server.data["rconpassword"] = "secret-query-password"

    mod.sync_server_config(server)

    gameplay = (tmp_path / "home/.config/SCP Secret Laboratory/config/7777/config_gameplay.txt").read_text()
    assert "server_name: AlphaGSM SCP" in gameplay
    assert "contact_email: ops@example.com" in gameplay
    assert "query_port_shift: 1111" in gameplay
    assert "query_administrator_password: secret-query-password" in gameplay
    assert "enable_query: true" in gameplay


def test_setting_schema_and_config_sync_keys_cover_canonical_surface():
    assert mod.config_sync_keys == ("servername", "contactemail", "queryport", "rconpassword")
    assert mod.setting_schema["servername"].storage_key == "servername"
    assert mod.setting_schema["queryport"].storage_key == "queryport"
    assert mod.setting_schema["rconpassword"].secret is True


def test_checkvalue_accepts_canonical_scpsl_keys():
    server = DummyServer()
    assert mod.checkvalue(server, ("servername",), "AlphaGSM SCP") == "AlphaGSM SCP"
    assert mod.checkvalue(server, ("contactemail",), "ops@example.com") == "ops@example.com"
    assert mod.checkvalue(server, ("queryport",), "8888") == 8888
    assert mod.checkvalue(server, ("rconpassword",), "secret-query-password") == "secret-query-password"


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


def test_get_container_spec_uses_container_local_home_paths(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "LocalAdmin"
    server.data["port"] = 27015
    server.data["queryport"] = 27016
    server.data["contactemail"] = "ops@example.com"
    (tmp_path / "LocalAdmin").write_text("")

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server"
    assert spec["env"] == {
        "HOME": "/srv/server/home",
        "XDG_CONFIG_HOME": "/srv/server/home/.config",
    }
    assert spec["command"] == ["./LocalAdmin", "27015"]
    gameplay = (tmp_path / "home/.config/SCP Secret Laboratory/config/27015/config_gameplay.txt").read_text()
    assert "enable_query: true" in gameplay
    assert "contact_email: ops@example.com" in gameplay


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
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="172.18.0.15") as resolver:
        assert mod.get_query_address(server) == ("172.18.0.15", 7778, "tcp")
    resolver.assert_called_once_with(server)


def test_get_info_address():
    server = DummyServer()
    server.data["queryport"] = 7778
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="172.18.0.15") as resolver:
        assert mod.get_info_address(server) == ("172.18.0.15", 7778, "tcp")
    resolver.assert_called_once_with(server)


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
