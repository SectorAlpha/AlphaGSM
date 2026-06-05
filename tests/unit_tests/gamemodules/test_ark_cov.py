"""Full coverage tests for ark."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.ark', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.ark as mod
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


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["adminpassword"] = "test"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["serverpassword"] = "test"
    server.data["sessionname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ShooterGame/Binaries/Linux/ShooterGameServer"
    server.data["Steam_AppID"] = 376030
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 376030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 376030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 376030
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
    server.data["exe_name"] = "ShooterGame/Binaries/Linux/ShooterGameServer"
    exe_path = tmp_path / "ShooterGame/Binaries/Linux/ShooterGameServer"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["adminpassword"] = "test"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["serverpassword"] = "test"
    server.data["sessionname"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cmd[0] == "./ShooterGame/Binaries/Linux/ShooterGameServer"
    assert cwd == server.data["dir"]


def test_get_start_command_sanitizes_sessionname_spaces(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ShooterGame/Binaries/Linux/ShooterGameServer"
    exe_path = tmp_path / "ShooterGame/Binaries/Linux/ShooterGameServer"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["adminpassword"] = "test"
    server.data["map"] = "TheIsland"
    server.data["maxplayers"] = 70
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["serverpassword"] = ""
    server.data["sessionname"] = "AlphaGSM itark"
    cmd, _cwd = mod.get_start_command(server)
    assert "SessionName=AlphaGSM_itark" in cmd[1]
    assert "SessionName=AlphaGSM itark" not in cmd[1]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["adminpassword"] = "test"
    server.data["map"] = "test"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["serverpassword"] = "test"
    server.data["sessionname"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


def test_get_query_address():
    server = DummyServer()
    server.data["queryport"] = 27015
    mod.runtime_module.resolve_query_host.return_value = "127.0.0.1"
    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "a2s")


def test_get_info_address():
    server = DummyServer()
    server.data["queryport"] = 27015
    mod.runtime_module.resolve_query_host.return_value = "127.0.0.1"
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "a2s")


def test_get_runtime_requirements_mounts(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path)
    mod.steamcmd.STEAMCMD_DIR = "/tmp/steamcmd"
    requirements = mod.get_runtime_requirements(server)
    assert requirements["family"] == "steamcmd-linux"
    assert any(
        mount["target"] == "/srv/server" for mount in requirements["mounts"]
    )
    assert any(
        mount["target"] == mod.CONTAINER_STEAMCMD_DIR
        for mount in requirements["mounts"]
    )


def test_get_container_spec_uses_non_root_steam_bootstrap(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path)
    server.data["exe_name"] = "ShooterGame/Binaries/Linux/ShooterGameServer"
    exe_path = tmp_path / "ShooterGame/Binaries/Linux/ShooterGameServer"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["adminpassword"] = "test"
    server.data["map"] = "TheIsland"
    server.data["maxplayers"] = 70
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["serverpassword"] = ""
    server.data["sessionname"] = "AlphaGSM itark"
    mod.steamcmd.STEAMCMD_DIR = "/tmp/steamcmd"
    spec = mod.get_container_spec(server)
    assert spec["working_dir"] == "/srv/server"
    assert spec["stdin_open"] is True
    shell = spec["command"][-1]
    assert "/home/alphagsm/.steam/sdk64/steamclient.so" in shell
    assert "/opt/alphagsm-steamcmd/linux64/steamclient.so" in shell
    assert "runuser -u alphagsm" in shell
    assert "./ShooterGame/Binaries/Linux/ShooterGameServer" in shell


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


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_map():
    server = DummyServer()
    result = mod.checkvalue(server, ("map",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_sessionname():
    server = DummyServer()
    result = mod.checkvalue(server, ("sessionname",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "/test/value")
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
