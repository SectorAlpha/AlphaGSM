"""Full coverage tests for longvinterserver."""

import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.longvinterserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.longvinterserver as mod
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
    assert server.data["configfile"] == "Longvinter/Saved/Config/LinuxServer/Game.ini"
    assert "queryport" not in server.data


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "LongvinterServer.sh"
    server.data["Steam_AppID"] = 1639880
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1639880
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1639880
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 1639880
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
    server.data["exe_name"] = "LongvinterServer.sh"
    server.data["port"] = 7777
    (tmp_path / "LongvinterServer.sh").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./LongvinterServer.sh",
        "-Port=7777",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert "queryport" not in mod.setting_schema


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


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "64")
    assert result == 64


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
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


def test_sync_server_config_copies_default_and_updates_values(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "configfile": "Longvinter/Saved/Config/LinuxServer/Game.ini",
            "servername": "AlphaGSM Longvinter",
            "maxplayers": 48,
        }
    )
    default_path = tmp_path / "Longvinter" / "Saved" / "Config" / "LinuxServer" / "Game.ini.default"
    default_path.parent.mkdir(parents=True)
    default_path.write_text(
        "[/Script/Longvinter.LVGameSession]\nServerName=Unnamed Island\nMaxPlayers=32\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    config_text = (tmp_path / "Longvinter" / "Saved" / "Config" / "LinuxServer" / "Game.ini").read_text(encoding="utf-8")
    assert "ServerName=AlphaGSM Longvinter" in config_text
    assert "MaxPlayers=48" in config_text


def test_sync_server_config_noops_without_template_or_config(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "configfile": "Longvinter/Saved/Config/LinuxServer/Game.ini",
            "servername": "AlphaGSM Longvinter",
            "maxplayers": 48,
        }
    )

    mod.sync_server_config(server)

    assert not (tmp_path / "Longvinter" / "Saved" / "Config" / "LinuxServer" / "Game.ini").exists()


def test_query_and_info_addresses_use_game_port():
    server = DummyServer()
    server.data["port"] = 7777
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == ("127.0.0.1", 7777, "udp")
        assert mod.get_info_address(server) == ("127.0.0.1", 7777, "udp")


def test_runtime_requirements_publish_only_game_udp_port(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "port": 7777})

    requirements = mod.get_runtime_requirements(server)

    assert requirements["family"] == "steamcmd-linux"
    assert requirements["ports"] == [{"host": 7777, "container": 7777, "protocol": "udp"}]


def test_get_container_spec_runs_server_as_matching_non_root_user(tmp_path):
    server = DummyServer()
    server.data.update({"dir": str(tmp_path) + "/", "exe_name": "LongvinterServer.sh", "port": 7777})
    (tmp_path / "LongvinterServer.sh").write_text("#!/bin/sh\n", encoding="utf-8")

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server"
    assert spec["command"][:2] == ["sh", "-lc"]
    shell_command = spec["command"][2]
    assert "runuser -u alphagsm -- ./LongvinterServer.sh -Port=7777" in shell_command
    assert "stat -c %u /srv/server" in shell_command
    assert "useradd -M -u \"$uid\" -g \"$gid\" -o alphagsm" in shell_command
    assert "groupadd -o -g \"$gid\" alphagsm" in shell_command
