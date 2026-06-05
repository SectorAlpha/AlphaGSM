"""Full coverage tests for heatserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.heatserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.heatserver as mod
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


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27015
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["startmap"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27016", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Server.exe"
    server.data["Steam_AppID"] = 996600
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 996600
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 996600
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 996600
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "Server.exe"
    (tmp_path / "Server.exe").write_text("")
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["startmap"] = "test"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == ["Server.exe"]
    assert cwd == server.data["dir"]


def test_wrap_linux_command_uses_xvfb_when_available(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/xvfb-run" if name == "xvfb-run" else None)
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda cmd, wineprefix=None, prefer_proton=False: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "STEAM_COMPAT_DATA_PATH=/tmp/proton",
            "STEAM_COMPAT_CLIENT_INSTALL_PATH=",
            "/opt/proton/proton",
            "run",
            *cmd,
        ],
    )
    monkeypatch.setattr(
        mod.proton,
        "prepend_env_assignments",
        lambda command, **env_vars: [
            "env",
            *list(command[1:1]),
            *[f"{key}={value}" for key, value in env_vars.items()],
            *command[1:],
        ] if command and command[0] == "env" else [
            "env",
            *[f"{key}={value}" for key, value in env_vars.items()],
            *command,
        ],
    )

    wrapped = mod._wrap_linux_command(["Server.exe", "-batchmode"], wineprefix="/tmp/proton")

    assert wrapped[:4] == [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        "env",
    ]
    assert "TERM=dumb" in wrapped
    assert "SDL_VIDEODRIVER=x11" in wrapped
    assert "SDL_AUDIODRIVER=dummy" in wrapped
    assert "STEAM_COMPAT_DATA_PATH=/tmp/proton" in wrapped
    assert "STEAM_COMPAT_CLIENT_INSTALL_PATH=" in wrapped
    assert "DISPLAY=" not in wrapped
    assert "WINEDLLOVERRIDES=winex11.drv=" not in wrapped
    assert wrapped[-4:] == ["/opt/proton/proton", "run", "Server.exe", "-batchmode"]


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["maxplayers"] = 27015
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    server.data["startmap"] = "test"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_sync_server_config_updates_native_settings(tmp_path):
    server = DummyServer("heat")
    server.data.update(
        {
            "dir": str(tmp_path),
            "port": "28015",
            "queryport": "28016",
            "maxplayers": "24",
            "startmap": "Smallville",
        }
    )
    config_dir = tmp_path / "Configuration"
    config_dir.mkdir()
    config_path = config_dir / "ServerSettings.cfg"
    config_path.write_text(
        "\n".join(
            [
                "portNumber = '7450'",
                "steamAuthPort = '27015'",
                "maxPlayers = '40'",
                "levelName = 'America'",
            ]
        ),
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    updated = config_path.read_text(encoding="utf-8")
    assert "portNumber = '28015'" in updated
    assert "steamAuthPort = '28016'" in updated
    assert "maxPlayers = '24'" in updated
    assert "levelName = 'Smallville'" in updated


def test_sync_server_config_missing_key_raises(tmp_path):
    server = DummyServer("heat")
    server.data.update({"dir": str(tmp_path), "port": "28015"})
    config_dir = tmp_path / "Configuration"
    config_dir.mkdir()
    config_path = config_dir / "ServerSettings.cfg"
    config_path.write_text("portNumber = '7450'\n", encoding="utf-8")

    with pytest.raises(ServerError, match="missing steamAuthPort"):
        mod.sync_server_config(server)


def test_build_default_server_settings_uses_current_server_values():
    server = DummyServer("heat")
    server.data.update(
        {
            "port": "28015",
            "queryport": "28016",
            "maxplayers": "24",
            "startmap": "Smallville",
            "servername": "AlphaGSM Heat Test",
        }
    )

    config_text = mod._build_default_server_settings(server)

    assert "serverName = 'AlphaGSM Heat Test'" in config_text
    assert "maxPlayers = '24'" in config_text
    assert "portNumber = '28015'" in config_text
    assert "steamAuthPort = '28016'" in config_text
    assert "asyncPort = '28019'" in config_text
    assert "pingPort = '28015'" in config_text
    assert "levelName = 'Smallville'" in config_text


def test_bootstrap_server_settings_falls_back_to_default_template(tmp_path, monkeypatch):
    server = DummyServer("heat")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "Server.exe",
            "port": "28015",
            "queryport": "28016",
            "maxplayers": "24",
            "startmap": "Smallville",
        }
    )
    (tmp_path / "Server.exe").write_text("", encoding="utf-8")

    class _DummyProcess:
        def poll(self):
            return 1

        def terminate(self):
            return None

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(
        mod,
        "get_start_command",
        lambda current: (["Server.exe"], current.data["dir"]),
    )
    monkeypatch.setattr(mod.subprocess, "Popen", lambda *args, **kwargs: _DummyProcess())

    mod._bootstrap_server_settings_if_missing(server)

    config_text = (tmp_path / "Configuration" / "ServerSettings.cfg").read_text(
        encoding="utf-8"
    )
    assert "portNumber = '28015'" in config_text
    assert "steamAuthPort = '28016'" in config_text


def test_sync_server_config_noops_without_install_dir():
    server = DummyServer("heat")
    server.data["port"] = "28015"

    mod.sync_server_config(server)


def test_query_and_info_address_use_queryport(monkeypatch):
    server = DummyServer("heat")
    server.data["queryport"] = "27016"
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 27016, "a2s")
    assert mod.get_info_address(server) == ("10.0.0.10", 27016, "a2s")


def test_prestart_syncs_server_config(tmp_path, monkeypatch):
    server = DummyServer("heat")
    server.data["dir"] = str(tmp_path)
    called = []
    monkeypatch.setattr(mod, "_bootstrap_server_settings_if_missing", lambda current: None)
    monkeypatch.setattr(mod, "sync_server_config", lambda current: called.append(current))

    mod.prestart(server)

    assert called == [server]


def test_prestart_bootstraps_missing_server_settings_before_sync(tmp_path, monkeypatch):
    server = DummyServer("heat")
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "Server.exe",
        }
    )
    (tmp_path / "Server.exe").write_text("", encoding="utf-8")
    bootstrap_calls = []
    sync_calls = []

    monkeypatch.setattr(mod, "_bootstrap_server_settings_if_missing", lambda current: bootstrap_calls.append(current))
    monkeypatch.setattr(mod, "sync_server_config", lambda current: sync_calls.append(current))

    mod.prestart(server)

    assert bootstrap_calls == [server]
    assert sync_calls == [server]


def test_do_stop():
    server = DummyServer()
    mod.runtime_module.send_to_server = MagicMock()
    mod.do_stop(server, 0)
    mod.runtime_module.send_to_server.assert_called_once_with(server, "\003")


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
