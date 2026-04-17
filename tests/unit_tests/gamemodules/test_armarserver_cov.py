"""Full coverage tests for armarserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.armarserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.armarserver as mod
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
    mod.configure(server, ask=False, port=2001, dir=str(tmp_path))
    assert server.data['port'] == 2001
    assert server.data['queryport'] == 2002
    assert server.data['scenarioid'] == mod.DEFAULT_SCENARIO_ID
    assert server.data['maxplayers'] == 8


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 2001
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["bindaddress"] = "test"
    server.data["configfile"] = "test"
    server.data["profilesdir"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["2002", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.name = "armar-alpha"
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ArmaReforgerServer"
    server.data["Steam_AppID"] = 1874900
    server.data["Steam_anonymous_login_possible"] = True
    server.data["configfile"] = "configs/server.json"
    server.data["profilesdir"] = "profile"
    server.data["bindaddress"] = "0.0.0.0"
    server.data["port"] = 2001
    server.data["queryport"] = 2002
    server.data["scenarioid"] = mod.DEFAULT_SCENARIO_ID
    server.data["maxplayers"] = 8
    mod.install(server)
    assert (tmp_path / "configs" / "server.json").is_file()
    assert (tmp_path / "profile").is_dir()
    config = (tmp_path / "configs" / "server.json").read_text()
    assert '"a2s": {' in config
    assert '"address": "0.0.0.0"' in config
    assert '"port": 2002' in config
    assert '"scenarioId": "{ECC61978EDCC2B5A}Missions/23_Campaign.conf"' in config
    assert '"maxPlayers": 8' in config


def test_sync_server_config_updates_existing_config(tmp_path):
    server = DummyServer()
    server.name = "armar-alpha"
    server.data["dir"] = str(tmp_path) + "/"
    server.data["configfile"] = "configs/server.json"
    server.data["profilesdir"] = "profile"
    server.data["bindaddress"] = "127.0.0.1"
    server.data["port"] = 2101
    server.data["queryport"] = 2102
    server.data["scenarioid"] = "scenario-custom"
    server.data["maxplayers"] = 12

    mod.sync_server_config(server)

    config = (tmp_path / "configs" / "server.json").read_text()
    assert '"address": "127.0.0.1"' in config
    assert '"port": 2102' in config
    assert '"scenarioId": "scenario-custom"' in config
    assert '"maxPlayers": 12' in config
    assert (tmp_path / "profile").is_dir()


def test_setting_schema_exposes_canonical_json_keys():
    schema = mod.setting_schema

    assert schema["map"].storage_key == "scenarioid"
    assert schema["map"].aliases == ("scenario", "scenarioid")
    assert schema["port"].storage_key is None
    assert schema["queryport"].storage_key is None
    assert schema["maxplayers"].storage_key is None
    assert schema["bindaddress"].storage_key is None
    assert schema["adminpassword"].storage_key is None
    assert schema["adminpassword"].secret is True
    assert schema["bindaddress"].apply_to == ("datastore", "native_config")
    assert schema["adminpassword"].apply_to == ("datastore", "native_config")


def test_checkvalue_accepts_json_synced_keys():
    server = DummyServer()

    assert mod.checkvalue(server, ("bindaddress",), "127.0.0.1") == "127.0.0.1"
    assert mod.checkvalue(server, ("adminpassword",), "secret") == "secret"


def test_sync_server_config_writes_json_backed_keys(tmp_path):
    server = DummyServer()
    server.name = "armar-alpha"
    server.data["dir"] = str(tmp_path) + "/"
    server.data["configfile"] = "configs/server.json"
    server.data["profilesdir"] = "profile"
    server.data["bindaddress"] = "127.0.0.1"
    server.data["port"] = 2201
    server.data["queryport"] = 2202
    server.data["scenarioid"] = "scenario-custom"
    server.data["adminpassword"] = "admin-secret"

    mod.sync_server_config(server)

    config = (tmp_path / "configs" / "server.json").read_text()
    assert '"address": "127.0.0.1"' in config
    assert '"port": 2202' in config
    assert '"scenarioId": "scenario-custom"' in config
    assert '"passwordAdmin": "admin-secret"' in config


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1874900
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1874900
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1874900
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
    server.data["exe_name"] = "ArmaReforgerServer"
    (tmp_path / "ArmaReforgerServer").write_text("")
    server.data["bindaddress"] = "test"
    server.data["configfile"] = "configs/server.json"
    server.data["port"] = 27015
    server.data["profilesdir"] = "profile"
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "server.json").write_text("{}\n")
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cmd[2] == str(tmp_path / "configs" / "server.json")
    assert cmd[4] == str(tmp_path / "profile")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["bindaddress"] = "test"
    server.data["configfile"] = "configs/server.json"
    server.data["port"] = 27015
    server.data["profilesdir"] = "profile"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_start_command_missing_config(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ArmaReforgerServer"
    (tmp_path / "ArmaReforgerServer").write_text("")
    server.data["bindaddress"] = "test"
    server.data["configfile"] = "configs/server.json"
    server.data["port"] = 27015
    server.data["profilesdir"] = "profile"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.screen.send_to_server.assert_called()


def test_get_query_address():
    server = DummyServer()
    server.data["port"] = 2302
    server.data["queryport"] = 17777
    assert mod.get_query_address(server) == ("127.0.0.1", 17777, "a2s")


def test_get_info_address_matches_query():
    server = DummyServer()
    server.data["port"] = 2302
    server.data["queryport"] = 17777
    assert mod.get_info_address(server) == ("127.0.0.1", 17777, "a2s")


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
    result = mod.checkvalue(server, ("queryport",), "17777")
    assert result == 17777


def test_checkvalue_configfile():
    server = DummyServer()
    result = mod.checkvalue(server, ("configfile",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_profilesdir():
    server = DummyServer()
    result = mod.checkvalue(server, ("profilesdir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_bindaddress():
    server = DummyServer()
    result = mod.checkvalue(server, ("bindaddress",), "/test/value")
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


def test_checkvalue_maxplayers():
    server = DummyServer()
    assert mod.checkvalue(server, ("maxplayers",), "12") == 12


def test_checkvalue_scenarioid():
    server = DummyServer()
    value = "{ECC61978EDCC2B5A}Missions/23_Campaign.conf"
    assert mod.checkvalue(server, ("scenarioid",), value) == value
