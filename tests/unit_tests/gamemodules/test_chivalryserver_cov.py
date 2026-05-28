"""Full coverage tests for chivalryserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.chivalryserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.chivalryserver as mod
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
    assert server.data['queryport'] == 27015


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Linux/UDKGameServer-Linux"
    server.data["Steam_AppID"] = 220070
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 220070
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 220070
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 220070
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_sync_server_config_updates_engine_ports(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 7779
    server.data["queryport"] = 27019
    config_path = tmp_path / "UDKGame" / "Config" / "PCServer-UDKEngine.ini"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("Port=7777\nPeerPort=7778\nQueryPort=27015\nOther=1\n")

    mod.sync_server_config(server)

    assert config_path.read_text() == (
        "Port=7779\n"
        "PeerPort=7780\n"
        "QueryPort=27019\n"
        "Other=1\n"
    )


def test_prestart_syncs_engine_config(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 8888
    server.data["queryport"] = 28015
    config_path = tmp_path / "UDKGame" / "Config" / "PCServer-UDKEngine.ini"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("Other=1\n")

    mod.prestart(server)

    assert config_path.read_text() == (
        "Other=1\n"
        "Port=8888\n"
        "PeerPort=8889\n"
        "QueryPort=28015\n"
    )


def test_get_start_command(tmp_path, monkeypatch):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Binaries/Linux/UDKGameServer-Linux"
    exe_path = tmp_path / "Binaries/Linux/UDKGameServer-Linux"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    loader_dir = tmp_path / "Binaries/Linux/lib"
    loader_dir.mkdir(parents=True, exist_ok=True)
    (loader_dir / "libPhysXLoader.so.1").write_text("")
    server.data["startmap"] = "test"
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    monkeypatch.setenv("LD_LIBRARY_PATH", "/existing/lib")
    cmd, cwd = mod.get_start_command(server)
    assert cmd[0] == "env"
    assert cmd[1] == (
        "LD_LIBRARY_PATH=%s:%s:%s:%s:%s:/existing/lib"
        % (
            os.path.join(mod.steamcmd.STEAMCMD_DIR, "linux32"),
            str(tmp_path),
            str(tmp_path / "linux64"),
            str(tmp_path / "Binaries" / "Linux"),
            str(tmp_path / "Binaries" / "Linux" / "lib"),
        )
    )
    assert cmd[2:] == [
        "./UDKGameServer-Linux",
        "test?Port=7777?QueryPort=27015?steamsockets",
        "-Port=7777",
        "-PeerPort=7778",
        "-QueryPort=27015",
        "-SEEKFREELOADINGSERVER",
    ]
    assert cwd == str(tmp_path / "Binaries" / "Linux")
    assert os.path.islink(loader_dir / "PhysXUpdateLoader.so")
    assert os.readlink(loader_dir / "PhysXUpdateLoader.so") == "libPhysXLoader.so.1"


def test_query_and_info_address_use_queryport(monkeypatch):
    server = DummyServer("chiv")
    server.data["queryport"] = "27015"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.9")

    assert mod.get_query_address(server) == ("10.0.0.9", 27015, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.9", 27015, "a2s")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "27015")
    assert result == 27015


def test_checkvalue_startmap():
    server = DummyServer()
    result = mod.checkvalue(server, ("startmap",), "/test/value")
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
