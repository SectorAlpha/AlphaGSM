"""Full coverage tests for atlasserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.atlasserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.atlasserver as mod
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
    mod.configure(server, ask=False, port=57555, dir=str(tmp_path))
    assert server.data['port'] == 57555


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 57555
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
    inputs = iter(["57556", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ShooterGame/Binaries/Linux/ShooterGameServer"
    server.data["Steam_AppID"] = 1006030
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1006030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1006030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1006030
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


def test_query_and_info_address_use_queryport(monkeypatch):
    server = DummyServer("atlas")
    server.data["queryport"] = "57561"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 57561, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.10", 57561, "a2s")


def test_runtime_requirements_and_container_spec_use_steamcmd_linux_family(tmp_path):
    server = DummyServer("atlas")
    exe_path = tmp_path / "ShooterGame" / "Binaries" / "Linux" / "ShooterGameServer"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    steamclient_path = tmp_path / "linux64" / "steamclient.so"
    steamclient_path.parent.mkdir(parents=True, exist_ok=True)
    steamclient_path.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "ShooterGame/Binaries/Linux/ShooterGameServer",
            "adminpassword": "test",
            "map": "Ocean",
            "maxplayers": 100,
            "port": 57555,
            "queryport": 57561,
            "serverpassword": "",
            "sessionname": "AlphaGSM atlas",
        }
    )

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["engine"] == "docker"
    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [
        {"host": 57561, "container": 57561, "protocol": "udp"},
        {"host": 57561, "container": 57561, "protocol": "tcp"},
        {"host": 57555, "container": 57555, "protocol": "udp"},
        {"host": 57555, "container": 57555, "protocol": "tcp"},
    ]
    assert spec["working_dir"] == "/srv/server"
    assert spec["env"]["HOME"] == "/srv/server"
    assert spec["env"]["LD_LIBRARY_PATH"].startswith(
        "/srv/server:/srv/server/linux64:/srv/server/ShooterGame/Binaries/Linux"
    )
    assert spec["command"][0] == "./ShooterGame/Binaries/Linux/ShooterGameServer"
    assert spec["command"][2:] == ["-server", "-log"]
    assert spec["stdin_open"] is True
    assert (tmp_path / "steam_appid.txt").read_text(encoding="utf-8") == "1006030\n"
    steamclient_link = tmp_path / ".steam" / "sdk64" / "steamclient.so"
    assert steamclient_link.is_symlink()
    assert steamclient_link.resolve() == steamclient_path


def test_do_stop_uses_runtime_send_to_server(monkeypatch):
    server = DummyServer()
    calls = []

    monkeypatch.setattr(mod.runtime_module, "send_to_server", lambda current, text: calls.append((current, text)))

    mod.do_stop(server, 0)

    assert calls == [(server, "\nquit\n")]


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


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "/test/value")
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
