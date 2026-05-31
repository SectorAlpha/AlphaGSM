"""Full coverage tests for tiserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.tiserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.tiserver as mod
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
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data["eos_client_id"] == ""
    assert server.data["eos_client_secret"] == ""


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["map"] = "test"
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
    server.data["exe_name"] = "TheIsleServer.sh"
    server.data["Steam_AppID"] = 412680
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 412680
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 412680
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 412680
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
    server.data["exe_name"] = "TheIsleServer.sh"
    (tmp_path / "TheIsleServer.sh").write_text("")
    server.data["map"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["eos_client_id"] = "client-id"
    server.data["eos_client_secret"] = "client-secret"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./TheIsleServer.sh",
        "test",
        "-Port=27015",
        "-QueryPort=27015",
        "-log",
        "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientId=client-id",
        "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientSecret=client-secret",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_theisle_launch_formats():
    assert mod.setting_schema["map"].launch_arg_format == "{value}"
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"


def test_get_provider_requirements_declares_eos_credentials():
    server = DummyServer()
    requirements = mod.get_provider_requirements(server)
    assert requirements == [
        {
            "provider": "eos",
            "kind": "credential",
            "keys": ("eos_client_id", "eos_client_secret"),
            "required_for": ("start",),
            "support_category": "provider-auth",
            "summary": "Epic Online Services dedicated-server credentials",
            "actions": (
                "Set eos_client_id and eos_client_secret before starting the server",
                "Use the official dedicated-server guide to create TheIsle/Saved/Config/LinuxServer/Engine.ini if you prefer file-based EOS configuration",
            ),
            "docs_slug": "tiserver",
        }
    ]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["map"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_start_command_missing_eos_credentials_raises_auth(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "TheIsleServer.sh"
    (tmp_path / "TheIsleServer.sh").write_text("")
    server.data["map"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError, match="ENABLED \\(AUTH\\)"):
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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_map():
    server = DummyServer()
    result = mod.checkvalue(server, ("map",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_eos_client_id():
    server = DummyServer()
    result = mod.checkvalue(server, ("eos_client_id",), "abc")
    assert result == "abc"


def test_checkvalue_eos_client_secret():
    server = DummyServer()
    result = mod.checkvalue(server, ("eos_client_secret",), "secret")
    assert result == "secret"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
