"""Full coverage tests for empyrionserver."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.modules.pop('gamemodules.empyrionserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.empyrionserver as mod
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
    mod.configure(server, ask=False, port=30000, dir=str(tmp_path))
    assert server.data['port'] == 30000
    assert server.data["queryport"] == "30003"


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 30000
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["queryport"] = 27015
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["30001", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "EmpyrionDedicated.exe"
    server.data["Steam_AppID"] = 530870
    server.data["Steam_anonymous_login_possible"] = True
    server.data["port"] = 31337
    (tmp_path / "dedicated.yaml").write_text(
        "ServerConfig:\n"
        "    Srv_Port: 30000\n",
        encoding="utf-8",
    )
    mod.install(server)
    assert (tmp_path / "dedicated.yaml").read_text(encoding="utf-8") == (
        "ServerConfig:\n"
        "    Srv_Port: 31337\n"
    )


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 530870
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 530870
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 530870
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception('already stopped'))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_sync_server_config_updates_dedicated_yaml_port(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 46319
    config_path = tmp_path / "dedicated.yaml"
    config_path.write_text(
        "ServerConfig:\r\n"
        "    Srv_Port: 30000\r\n"
        "    Srv_Name: My Server\r\n",
        encoding="utf-8",
    )

    mod.sync_server_config(server)

    assert config_path.read_text(encoding="utf-8") == (
        "ServerConfig:\n"
        "    Srv_Port: 46319\n"
        "    Srv_Name: My Server\n"
    )


def test_sync_server_config_missing_file_noops(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 46319

    mod.sync_server_config(server)

    assert not (tmp_path / "dedicated.yaml").exists()


def test_prestart_syncs_dedicated_yaml(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 42657
    config_path = tmp_path / "dedicated.yaml"
    config_path.write_text(
        "ServerConfig:\n"
        "    Srv_Port: 30000\n",
        encoding="utf-8",
    )

    mod.prestart(server)

    assert config_path.read_text(encoding="utf-8") == (
        "ServerConfig:\n"
        "    Srv_Port: 42657\n"
    )
    assert server.data["queryport"] == "42660"


def test_query_and_info_address_use_derived_tcp_listener(monkeypatch):
    server = DummyServer()
    server.data["port"] = 46319
    server.data["queryport"] = 30004
    monkeypatch.setattr(mod.runtime_module, "resolve_query_host", lambda current: "10.0.0.10")

    assert mod.get_query_address(server) == ("10.0.0.10", 46322, "tcp")
    assert mod.get_info_address(server) == ("10.0.0.10", 46322, "tcp")


def test_runtime_requirements_publish_game_udp_and_stcp_tcp(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 46319
    server.data["queryport"] = 30004

    requirements = mod.get_runtime_requirements(server)
    ports = {(entry["host"], entry["protocol"]) for entry in requirements["ports"]}

    assert (46319, "udp") in ports
    assert (46322, "tcp") in ports
    assert (46322, "udp") not in ports
    assert server.data["queryport"] == "46322"


def test_get_start_command(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", False)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "EmpyrionDedicated.exe"
    (tmp_path / "EmpyrionDedicated.exe").write_text("")
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)


def test_get_start_command_linux_uses_batchmode_dedicated_exe(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer/EmpyrionDedicated.exe"
    dedicated_dir = tmp_path / "DedicatedServer"
    dedicated_dir.mkdir()
    (dedicated_dir / "EmpyrionDedicated.exe").write_text("")

    captured = {}

    def fake_wrap(command, wineprefix=None, prefer_proton=False):
        captured["command"] = list(command)
        captured["wineprefix"] = wineprefix
        captured["prefer_proton"] = prefer_proton
        return ["wrapped", *command]

    monkeypatch.setattr(mod, "_wrap_linux_command", fake_wrap)

    cmd, cwd = mod.get_start_command(server)

    assert cmd == [
        "wrapped",
        "DedicatedServer/EmpyrionDedicated.exe",
        "-batchmode",
        "-nographics",
        "-logFile",
        "Logs/alphagsm-dedicated.log",
        "-dedicated",
        "dedicated.yaml",
    ]
    assert cwd == server.data["dir"]
    assert captured == {
        "command": [
            "DedicatedServer/EmpyrionDedicated.exe",
            "-batchmode",
            "-nographics",
            "-logFile",
            "Logs/alphagsm-dedicated.log",
            "-dedicated",
            "dedicated.yaml",
        ],
        "wineprefix": None,
        "prefer_proton": True,
    }


def test_wrap_linux_command_uses_xvfb_when_available(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda name: "/usr/bin/xvfb-run" if name == "xvfb-run" else None)
    captured = {}

    def fake_wrap(command, wineprefix=None, prefer_proton=False):
        captured["prefer_proton"] = prefer_proton
        return [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "wine",
            *command,
        ]

    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        fake_wrap,
    )
    monkeypatch.setattr(
        mod.proton,
        "prepend_env_assignments",
        lambda cmd, **env: (
            [cmd[0], *(f"{key}={value}" for key, value in env.items()), *cmd[1:]]
            if cmd and cmd[0] == "env"
            else ["env", *(f"{key}={value}" for key, value in env.items()), *cmd]
        ),
    )

    wrapped = mod._wrap_linux_command(["DedicatedServer/EmpyrionDedicated.exe"])

    assert captured["prefer_proton"] is False
    assert wrapped == [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        "env",
        "SDL_VIDEODRIVER=x11",
        "SDL_AUDIODRIVER=dummy",
        "wine",
        "DedicatedServer/EmpyrionDedicated.exe",
    ]


def test_linux_dedicated_log_path_constant_is_root_logs_file():
    assert mod._LINUX_DEDICATED_LOG == os.path.join("Logs", "alphagsm-dedicated.log")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    with pytest.raises(ServerError):
        mod.get_start_command(server)


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
