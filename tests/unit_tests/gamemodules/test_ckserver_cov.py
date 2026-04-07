"""Full coverage tests for ckserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.ckserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.ckserver as mod
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
    mod.configure(server, ask=False, port=27015, dir=str(tmp_path))
    assert server.data['port'] == 27015
    assert server.data['exe_name'] == '_launch.sh'
    assert server.data['worldindex'] == '0'


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["world"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "CoreKeeperServer"
    server.data["Steam_AppID"] = 1963720
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_patch_launch_script_rewrites_upstream_xvfb_block(tmp_path):
    launch = tmp_path / "_launch.sh"
    launch.write_text(
        "#!/bin/bash\n\n"
        "if [[ -z \"${PRESSURE_VESSEL_RUNTIME}\" ]]\n"
        "then\n"
        "    set -m\n\n"
        "    rm -f /tmp/.X99-lock\n\n"
        "    Xvfb :99 -screen 0 1x1x24 -nolisten tcp &\n"
        "    xvfbpid=$!\n\n"
        "    DISPLAY=:99 LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH:$installdir/linux64/\" \\\n"
        "           \"$exepath\" -batchmode -logfile CoreKeeperServerLog.txt \"$@\" &\n"
        "fi\n",
        encoding="utf-8",
    )
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"

    mod._patch_launch_script(server)

    updated = launch.read_text(encoding="utf-8")
    assert "xvfb-run -a" in updated
    assert "Xvfb :99 -screen 0 1x1x24 -nolisten tcp &" not in updated


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1963720
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1963720
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1963720
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
    server.data["exe_name"] = "_launch.sh"
    (tmp_path / "_launch.sh").write_text("")
    server.data["maxplayers"] = 8
    server.data["port"] = 27015
    server.data["world"] = "test"
    server.data["worldindex"] = 0
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./_launch.sh",
        "-world",
        "0",
        "-worldname",
        "test",
        "-port",
        "27015",
        "-maxplayers",
        "8",
        "-datapath",
        str(tmp_path / "DedicatedServer"),
    ]
    assert cwd == str(tmp_path) + "/"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 8
    server.data["port"] = 27015
    server.data["world"] = "test"
    server.data["worldindex"] = 0
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_query_address():
    server = DummyServer()
    server.data["port"] = 27015
    assert mod.get_query_address(server) == ("127.0.0.1", 27015, "udp")


def test_get_info_address():
    server = DummyServer()
    server.data["port"] = 27015
    assert mod.get_info_address(server) == ("127.0.0.1", 27015, "udp")


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


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_world():
    server = DummyServer()
    result = mod.checkvalue(server, ("world",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_worldindex():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldindex",), "3")
    assert result == 3


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

