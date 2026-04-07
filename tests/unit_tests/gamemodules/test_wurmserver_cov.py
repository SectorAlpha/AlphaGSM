"""Full coverage tests for wurmserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.wurmserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.wurmserver as mod
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
    mod.configure(server, ask=False, port=3724, dir=str(tmp_path))
    assert server.data['port'] == 3724
    assert server.data['worldname'] == 'Adventure'
    assert server.data['queryport'] == 27016
    assert server.data['internalport'] == 7220
    assert server.data['rmiport'] == 7221


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 3724
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["internalport"] = 7220
    server.data["rmiport"] = 7221
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["worldname"] = "Adventure"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["3725", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "WurmServerLauncher"
    server.data["Steam_AppID"] = 402370
    server.data["Steam_anonymous_login_possible"] = True
    linux64 = tmp_path / "linux64"
    linux64.mkdir()
    (linux64 / "steamclient.so").write_text("steamclient")
    dist_adventure = tmp_path / "dist" / "Adventure"
    dist_adventure.mkdir(parents=True)
    (dist_adventure / "wurm.ini").write_text("adventure")
    dist_creative = tmp_path / "dist" / "Creative"
    dist_creative.mkdir(parents=True)
    (dist_creative / "wurm.ini").write_text("creative")
    mod.install(server)
    assert (tmp_path / "nativelibs" / "steamclient.so").read_text() == "steamclient"
    assert (tmp_path / "LaunchConfig.ini").read_text() == mod.DEFAULT_LAUNCH_CONFIG
    assert (tmp_path / "Adventure" / "wurm.ini").read_text() == "adventure"
    assert (tmp_path / "Creative" / "wurm.ini").read_text() == "creative"


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 402370
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 402370
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 402370
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
    server.data["exe_name"] = "WurmServerLauncher"
    (tmp_path / "WurmServerLauncher").write_text("")
    server.data["worldname"] = "Adventure"
    server.data["port"] = 3724
    server.data["queryport"] = 27016
    server.data["internalport"] = 7220
    server.data["rmiport"] = 7221
    server.data["servername"] = "AlphaGSM testserver"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./WurmServerLauncher",
        "start=Adventure",
        "ip=127.0.0.1",
        "externalport=3724",
        "queryport=27016",
        "rmiregport=7220",
        "rmiport=7221",
        "servername=AlphaGSM testserver",
    ]
    assert cwd == str(tmp_path) + "/"


def test_get_query_address():
    server = DummyServer()
    server.data["port"] = 3724
    assert mod.get_query_address(server) == ("127.0.0.1", 3724, "tcp")


def test_get_info_address():
    server = DummyServer()
    server.data["port"] = 3724
    assert mod.get_info_address(server) == ("127.0.0.1", 3724, "tcp")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
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


def test_checkvalue_port_rejects_out_of_range():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("port",), "58747")


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_internalport():
    server = DummyServer()
    result = mod.checkvalue(server, ("internalport",), "12345")
    assert result == 12345


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_javapath():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("javapath",), "/test/value")


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_rmiport():
    server = DummyServer()
    result = mod.checkvalue(server, ("rmiport",), "12346")
    assert result == 12346


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "Creative")
    assert result == "Creative"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")

