"""Full coverage tests for battlebitserver."""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from server.settable_keys import resolve_requested_key

sys.modules.pop("gamemodules.battlebitserver", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.battlebitserver as mod
    from server import ServerError

    mod.runtime_module.send_to_server = MagicMock()
    mod.proton = types.SimpleNamespace(
        wrap_command=MagicMock(side_effect=lambda cmd, **_: ["wrapped"] + list(cmd))
    )


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
    mod.configure(server, ask=False, port=29992, dir=str(tmp_path))
    assert server.data["port"] == 29992


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 29992
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 127
    server.data["servername"] = "AlphaGSM Test"
    server.data["apiendpoint"] = ""
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["29993", str(tmp_path / "custom")])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "BattleBit.exe"
    server.data["Steam_AppID"] = 689410
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 689410
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 689410
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 689410
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception("already stopped"))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_setting_schema_resolves_api_endpoint_alias():
    resolved = resolve_requested_key("api_endpoint", mod.setting_schema)

    assert resolved.canonical_key == "apiendpoint"
    assert resolved.storage_key == "apiendpoint"


def test_get_start_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "BattleBit.exe"
    (tmp_path / "BattleBit.exe").write_text("")
    server.data["maxplayers"] = 127
    server.data["port"] = 29992
    server.data["servername"] = "AlphaGSM BattleBit IT"
    server.data["apiendpoint"] = "127.0.0.1:29294"
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cwd == server.data["dir"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 127
    server.data["port"] = 29992
    server.data["apiendpoint"] = "127.0.0.1:29294"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_start_command_requires_apiendpoint(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "BattleBit.exe"
    (tmp_path / "BattleBit.exe").write_text("")
    server.data["maxplayers"] = 127
    server.data["port"] = 29992

    with pytest.raises(ServerError) as excinfo:
        mod.get_start_command(server)

    assert "ENABLED (AUTH)" in str(excinfo.value)


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
    server.data["backup"] = {
        "profiles": {"default": {"targets": ["saves"]}},
        "schedule": [("default", 0, "days")],
    }
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


def test_checkvalue_queryport_is_unsupported():
    server = DummyServer()
    with pytest.raises(ServerError):
        mod.checkvalue(server, ("queryport",), "12345")


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "AlphaGSM BattleBit")
    assert result == "AlphaGSM BattleBit"


def test_checkvalue_apiendpoint():
    server = DummyServer()
    result = mod.checkvalue(server, ("apiendpoint",), "127.0.0.1:29294")
    assert result == "127.0.0.1:29294"


def test_checkvalue_apitoken():
    server = DummyServer()
    result = mod.checkvalue(server, ("apitoken",), "secret-token")
    assert result == "secret-token"


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
    server.data["backup"] = {
        "profiles": {"default": {"targets": ["saves"]}},
        "schedule": [("default", 0, "days")],
    }
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
