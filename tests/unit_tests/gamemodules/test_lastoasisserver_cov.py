"""Full coverage tests for lastoasisserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.lastoasisserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.lastoasisserver as mod
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
    mod.configure(server, ask=False, port=15000, dir=str(tmp_path))
    assert server.data['port'] == 15000


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 15000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["worldname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["15001", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Mist/Binaries/Linux/MistServer-Linux-Shipping"
    server.data["Steam_AppID"] = 920720
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 920720
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 920720
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 920720
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
    exe_path = tmp_path / "Mist" / "Binaries" / "Linux" / "MistServer-Linux-Shipping"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")
    server.data["exe_name"] = "Mist/Binaries/Linux/MistServer-Linux-Shipping"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["worldname"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./Mist/Binaries/Linux/MistServer-Linux-Shipping",
        "-log",
        "-port=27015",
        "-queryport=27015",
        "-maxplayers=27015",
        "-worldname=test",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_lastoasis_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-queryport={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "-maxplayers={value}"
    assert mod.setting_schema["worldname"].launch_arg_format == "-worldname={value}"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["worldname"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called()


def test_get_container_spec_runs_server_as_matching_non_root_user(tmp_path):
    server = DummyServer()
    exe_path = tmp_path / "Mist" / "Binaries" / "Linux" / "MistServer-Linux-Shipping"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": "Mist/Binaries/Linux/MistServer-Linux-Shipping",
            "port": 15000,
            "queryport": 15001,
        }
    )

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][:2] == ["sh", "-lc"]
    shell_command = spec["command"][2]
    assert 'useradd -M -u 1000 -o alphagsm;' in shell_command
    assert 'mkdir -p /home/alphagsm/.steam/sdk64;' in shell_command
    assert 'chmod -R a+rwX /srv/server /home/alphagsm;' in shell_command
    assert (
        'ln -sfn /srv/server/linux64/steamclient.so '
        '/home/alphagsm/.steam/sdk64/steamclient.so;'
    ) in shell_command
    assert (
        "runuser -u alphagsm -- "
        "./Mist/Binaries/Linux/MistServer-Linux-Shipping -log -port=15000 -queryport=15001"
    ) in shell_command


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


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "/test/value")
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
