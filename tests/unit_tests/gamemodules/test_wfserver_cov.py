"""Full coverage tests for wfserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.wfserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.wfserver as mod
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
    mod.configure(server, ask=False, port=44400, dir=str(tmp_path))
    assert server.data['port'] == 44400


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 44400
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["fs_game"] = "test"
    server.data["hostname"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["44401", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "wf_server.x86_64"
    server.data["Steam_AppID"] = 1136510
    server.data["Steam_anonymous_login_possible"] = True
    server.data["hostname"] = "AlphaGSM Warfork"
    server.data["port"] = 44400
    mod.install(server)
    assert (tmp_path / "basewf" / "dedicated_autoexec.cfg").read_text() == 'set net_port 44400\nset sv_hostname "AlphaGSM Warfork"\n'


def test_sync_server_config_rewrites_autoexec(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["hostname"] = "AlphaGSM Warfork"
    server.data["port"] = 44401

    mod.sync_server_config(server)

    assert (tmp_path / "basewf" / "dedicated_autoexec.cfg").read_text() == 'set net_port 44401\nset sv_hostname "AlphaGSM Warfork"\n'


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1136510
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1136510
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1136510
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
    server.data["exe_name"] = "wf_server.x86_64"
    (tmp_path / "wf_server.x86_64").write_text("")
    server.data["fs_game"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./wf_server.x86_64",
        "+set",
        "fs_game",
        "test",
        "+set",
        "sv_hostname",
        "test",
        "+set",
        "net_ip",
        "0.0.0.0",
        "+set",
        "net_port",
        "27015",
        "+map",
        "test",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_warfork_launch_and_native_config_keys():
    assert mod.setting_schema["hostname"].native_config_key == "sv_hostname"
    assert mod.setting_schema["port"].native_config_key == "net_port"
    assert mod.setting_schema["bindaddress"].launch_arg_tokens == ("+set", "net_ip")
    assert mod.setting_schema["startmap"].aliases == ("map",)


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["fs_game"] = "test"
    server.data["hostname"] = "test"
    server.data["port"] = 27015
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_with(server, "\nquit\n")


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


def test_checkvalue_fs_game():
    server = DummyServer()
    result = mod.checkvalue(server, ("fs_game",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_startmap_validates_installed_maps(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["fs_game"] = "basewf"
    maps_dir = tmp_path / "basewf" / "maps"
    maps_dir.mkdir(parents=True)
    (maps_dir / "wfa1.bsp").write_text("")

    result = mod.checkvalue(server, ("startmap",), "wfa1")

    assert result == "wfa1"


def test_checkvalue_startmap_rejects_unknown_installed_map(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["fs_game"] = "basewf"
    maps_dir = tmp_path / "basewf" / "maps"
    maps_dir.mkdir(parents=True)
    (maps_dir / "wfa1.bsp").write_text("")

    with pytest.raises(ServerError, match="Unsupported map"):
        mod.checkvalue(server, ("startmap",), "missing_map")


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
