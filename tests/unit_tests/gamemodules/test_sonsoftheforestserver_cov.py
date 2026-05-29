"""Full coverage tests for sonsoftheforestserver."""

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from utils import proton as real_proton

sys.modules.pop('gamemodules.sonsoftheforestserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.sonsoftheforestserver as mod
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
    mod.configure(server, ask=False, port=8766, dir=str(tmp_path))
    assert server.data['port'] == 8766
    assert server.data['exe_name'] == 'SonsOfTheForestDS.exe'
    assert server.data["queryport"] == "27016"
    assert server.data["blobsyncport"] == "9700"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8766
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8767", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "SonsOfTheForestDS.exe"
    server.data["Steam_AppID"] = 2465200
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 41777
    server.data["queryport"] = 27026
    server.data["blobsyncport"] = 9706
    mod.install(server)
    config_path = tmp_path / "user-data" / "dedicatedserver.cfg"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["GamePort"] == 41777
    assert payload["QueryPort"] == 27026
    assert payload["BlobSyncPort"] == 9706
    assert payload["SkipNetworkAccessibilityTest"] is True
    assert (tmp_path / "steam_appid.txt").read_text(encoding="ascii") == "1326470\n"
    assert (tmp_path / "user-data" / "ownerswhitelist.txt").is_file()


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2465200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2465200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2465200
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_sync_server_config_writes_user_data_json(tmp_path):
    server = DummyServer("sotf-alpha")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 32123
    server.data["queryport"] = 32124
    server.data["blobsyncport"] = 32125

    mod.sync_server_config(server)

    config_path = tmp_path / "user-data" / "dedicatedserver.cfg"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload == {
        "IpAddress": "0.0.0.0",
        "GamePort": 32123,
        "QueryPort": 32124,
        "BlobSyncPort": 32125,
        "ServerName": "sotf-alpha",
        "MaxPlayers": 8,
        "Password": "",
        "LanOnly": False,
        "SaveSlot": 1,
        "SaveMode": "Continue",
        "GameMode": "Normal",
        "SaveInterval": 600,
        "IdleDayCycleSpeed": 0.0,
        "IdleTargetFramerate": 5,
        "ActiveTargetFramerate": 60,
        "LogFilesEnabled": True,
        "TimestampLogFilenames": False,
        "TimestampLogEntries": True,
        "SkipNetworkAccessibilityTest": True,
        "GameSettings": {},
        "CustomGameModeSettings": {},
    }
    assert (tmp_path / "steam_appid.txt").read_text(encoding="ascii") == "1326470\n"
    owners_whitelist_path = tmp_path / "user-data" / "ownerswhitelist.txt"
    assert owners_whitelist_path.read_text(encoding="utf-8") == mod._DEFAULT_OWNERS_WHITELIST


def test_prestart_refreshes_dedicatedserver_cfg(tmp_path):
    server = DummyServer("sotf-beta")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 41111
    server.data["queryport"] = 41112
    server.data["blobsyncport"] = 41113

    mod.prestart(server)

    config_path = tmp_path / "user-data" / "dedicatedserver.cfg"
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    assert payload["GamePort"] == 41111
    assert payload["QueryPort"] == 41112
    assert payload["BlobSyncPort"] == 41113
    assert (tmp_path / "steam_appid.txt").read_text(encoding="ascii") == "1326470\n"
    assert (tmp_path / "user-data" / "ownerswhitelist.txt").is_file()


def test_query_and_info_address_use_queryport(monkeypatch):
    server = DummyServer()
    server.data["queryport"] = "27016"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "127.0.0.2")

    assert mod.get_query_address(server) == ("127.0.0.2", 27016, "a2s")
    assert mod.get_info_address(server) == ("127.0.0.2", 27016, "a2s")


def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "SonsOfTheForestDS.exe"
    (tmp_path / "SonsOfTheForestDS.exe").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cmd == [
        "SonsOfTheForestDS.exe",
        "-userdatapath",
        "./user-data",
        "-batchmode",
        "-nographics",
        "-verboseLogging",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_linux_uses_wrapped_user_data_path(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    wrap_command = MagicMock(side_effect=lambda cmd, wineprefix=None: ["wrapped", *cmd])
    monkeypatch.setattr(mod, "_wrap_linux_command", wrap_command)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "SonsOfTheForestDS.exe"
    (tmp_path / "SonsOfTheForestDS.exe").write_text("")

    cmd, cwd = mod.get_start_command(server)

    wrap_command.assert_called_once()
    args, kwargs = wrap_command.call_args
    assert args == (
        [
            "SonsOfTheForestDS.exe",
            "-userdatapath",
            "./user-data",
            "-batchmode",
            "-nographics",
            "-verboseLogging",
        ],
    )
    assert kwargs == {"wineprefix": None}
    assert cmd == [
        "wrapped",
        "SonsOfTheForestDS.exe",
        "-userdatapath",
        "./user-data",
        "-batchmode",
        "-nographics",
        "-verboseLogging",
    ]
    assert cwd == server.data["dir"]


def test_get_container_start_command_uses_bare_windows_command(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "SonsOfTheForestDS.exe"
    (tmp_path / "SonsOfTheForestDS.exe").write_text("")

    cmd, cwd = mod._get_container_start_command(server)

    assert cmd == [
        "SonsOfTheForestDS.exe",
        "-userdatapath",
        "./user-data",
        "-batchmode",
        "-nographics",
        "-verboseLogging",
    ]
    assert cwd == server.data["dir"]


def test_wrap_linux_command_uses_xvfb_when_available(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/xvfb-run" if name == "xvfb-run" else None)
    monkeypatch.setattr(mod.proton, "prepend_env_assignments", real_proton.prepend_env_assignments)
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "wine",
            *cmd,
        ],
    )

    wrapped = mod._wrap_linux_command(["SonsOfTheForestDS.exe", "-verboseLogging"])

    assert wrapped == [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        "env",
        "SDL_VIDEODRIVER=x11",
        "SDL_AUDIODRIVER=dummy",
        "WINEDLLOVERRIDES=",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "SteamAppId=1326470",
        "SteamGameId=1326470",
        "wine",
        "SonsOfTheForestDS.exe",
        "-verboseLogging",
    ]


def test_wrap_linux_command_without_xvfb_keeps_wrapped_env(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: None)
    monkeypatch.setattr(mod.proton, "prepend_env_assignments", real_proton.prepend_env_assignments)
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: ["env", "wine", *cmd],
    )

    wrapped = mod._wrap_linux_command(["SonsOfTheForestDS.exe", "-verboseLogging"])

    assert wrapped == [
        "env",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "SteamAppId=1326470",
        "SteamGameId=1326470",
        "wine",
        "SonsOfTheForestDS.exe",
        "-verboseLogging",
    ]


def test_get_start_command_legacy_batch_prefers_server_exe(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "StartSOTFDedicated.bat"
    (tmp_path / "StartSOTFDedicated.bat").write_text("")
    (tmp_path / "SonsOfTheForestDS.exe").write_text("")

    cmd, _cwd = mod.get_start_command(server)

    assert cmd[0] == "SonsOfTheForestDS.exe"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    with patch.object(mod.runtime_module, "send_to_server") as send_to_server:
        mod.do_stop(server, 0)
    send_to_server.assert_called_once_with(server, "\003")


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


def test_checkvalue_blobsyncport():
    server = DummyServer()
    result = mod.checkvalue(server, ("blobsyncport",), "12346")
    assert result == 12346


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
