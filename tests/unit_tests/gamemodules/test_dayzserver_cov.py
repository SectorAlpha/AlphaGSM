"""Full coverage tests for dayzserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.dayzserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.dayzserver as mod
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
    mod.configure(server, ask=False, port=2302, dir=str(tmp_path))
    assert server.data['port'] == 2302


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 2302
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["configfile"] = "test"
    server.data["cpu_count"] = "test"
    server.data["profilesdir"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["2303", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DayZServer"
    server.data["Steam_AppID"] = 223350
    server.data["Steam_anonymous_login_possible"] = True
    server.data["configfile"] = "serverDZ.cfg"
    (tmp_path / "serverDZ.cfg").write_text('hostname = "Old Name";\n', encoding="utf-8")
    mod.install(server)


def test_sync_server_config_updates_serverdz_cfg_values(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["configfile"] = "serverDZ.cfg"
    server.data["hostname"] = "AlphaGSM DayZ Test"
    server.data["serverpassword"] = "joinsecret"
    server.data["adminpassword"] = "adminsecret"
    server.data["maxplayers"] = 48
    server.data["queryport"] = 2303
    config_path = tmp_path / "serverDZ.cfg"
    config_path.write_text(
        'hostname = "Old Name";\n'
        'password = "";\n'
        'passwordAdmin = "";\n'
        'maxPlayers = 60;\n'
        'steamQueryPort = 2304;\n'
        'verifySignatures = 2;\n',
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert config_path.read_text(encoding="utf-8").splitlines() == [
        'hostname = "AlphaGSM DayZ Test";',
        'password = "joinsecret";',
        'passwordAdmin = "adminsecret";',
        'maxPlayers = 48;',
        'steamQueryPort = 2303;',
        'verifySignatures = 2;',
    ]


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 223350
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 223350
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 223350
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
    server.data["exe_name"] = "DayZServer"
    (tmp_path / "DayZServer").write_text("")
    server.data["configfile"] = "test"
    server.data["cpu_count"] = "test"
    server.data["port"] = 27015
    server.data["profilesdir"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["configfile"] = "test"
    server.data["cpu_count"] = "test"
    server.data["port"] = 27015
    server.data["profilesdir"] = "test"
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
    result = mod.checkvalue(server, ("queryport",), "2303")
    assert result == 2303


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "40")
    assert result == 40


def test_checkvalue_configfile():
    server = DummyServer()
    result = mod.checkvalue(server, ("configfile",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_profilesdir():
    server = DummyServer()
    result = mod.checkvalue(server, ("profilesdir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_cpu_count():
    server = DummyServer()
    result = mod.checkvalue(server, ("cpu_count",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_hostname():
    server = DummyServer()
    result = mod.checkvalue(server, ("hostname",), "AlphaGSM DayZ")
    assert result == "AlphaGSM DayZ"


def test_checkvalue_serverpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("serverpassword",), "joinsecret")
    assert result == "joinsecret"


def test_checkvalue_adminpassword():
    server = DummyServer()
    result = mod.checkvalue(server, ("adminpassword",), "adminsecret")
    assert result == "adminsecret"


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

