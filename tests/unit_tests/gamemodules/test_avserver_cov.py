"""Full coverage tests for avserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.avserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.avserver as mod
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
    mod.configure(server, ask=False, port=27000, dir=str(tmp_path))
    assert server.data['port'] == 27000
    assert server.data['servername'] == 'AlphaGSM testserver'
    assert server.data['queryport'] == 27003
    assert server.data['steamqueryport'] == 27020
    assert server.data['steammasterport'] == 27021


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["administration"] = ""
    server.data["galaxy"] = "test"
    server.data["seed"] = "test"
    server.data["servername"] = "test"
    server.data["queryport"] = 27003
    server.data["steamqueryport"] = 27020
    server.data["steammasterport"] = 27021
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27001", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "server.sh"
    server.data["Steam_AppID"] = 565060
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 565060
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 565060
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 565060
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
    server.data["exe_name"] = "server.sh"
    (tmp_path / "server.sh").write_text("")
    server.data["administration"] = ""
    server.data["galaxy"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27018
    server.data["seed"] = "test"
    server.data["servername"] = "Test Avorion"
    server.data["steamqueryport"] = 27035
    server.data["steammasterport"] = 27036
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./server.sh",
        "--datapath",
        "./galaxies",
        "--galaxy-name",
        "test",
        "--server-name",
        "Test Avorion",
        "--port",
        "27015",
        "--query-port",
        "27018",
        "--steam-query-port",
        "27035",
        "--steam-master-port",
        "27036",
        "--seed",
        "test",
    ]
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_includes_admin_when_set(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "server.sh"
    (tmp_path / "server.sh").write_text("")
    server.data.update(
        {
            "administration": "76561198000000000",
            "galaxy": "test",
            "port": 27015,
            "queryport": 27018,
            "seed": "test",
            "servername": "Test Avorion",
            "steamqueryport": 27035,
            "steammasterport": 27036,
        }
    )
    cmd, _ = mod.get_start_command(server)
    assert cmd[-2:] == ["--admin", "76561198000000000"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["administration"] = ""
    server.data["galaxy"] = "test"
    server.data["port"] = 27015
    server.data["queryport"] = 27018
    server.data["seed"] = "test"
    server.data["servername"] = "Test Avorion"
    server.data["steamqueryport"] = 27035
    server.data["steammasterport"] = 27036
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_query_address():
    server = DummyServer()
    server.data["steamqueryport"] = 27020
    assert mod.get_query_address(server) == ("127.0.0.1", 27020, "udp")


def test_get_info_address():
    server = DummyServer()
    server.data["steamqueryport"] = 27020
    assert mod.get_info_address(server) == ("127.0.0.1", 27020, "udp")


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
    result = mod.checkvalue(server, ("queryport",), "12348")
    assert result == 12348


def test_checkvalue_steamqueryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("steamqueryport",), "12365")
    assert result == 12365


def test_checkvalue_steammasterport():
    server = DummyServer()
    result = mod.checkvalue(server, ("steammasterport",), "12366")
    assert result == 12366


def test_checkvalue_galaxy():
    server = DummyServer()
    result = mod.checkvalue(server, ("galaxy",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_seed():
    server = DummyServer()
    result = mod.checkvalue(server, ("seed",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_administration():
    server = DummyServer()
    result = mod.checkvalue(server, ("administration",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "Avorion Test")
    assert result == "Avorion Test"


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

