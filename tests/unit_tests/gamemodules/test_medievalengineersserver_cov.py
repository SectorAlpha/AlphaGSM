"""Full coverage tests for medievalengineersserver."""

import os
import sys
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.medievalengineersserver', None)
_proton_mock = MagicMock()
_proton_mock.wrap_command.side_effect = lambda cmd, wineprefix=None, prefer_proton=False: list(cmd)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock(), 'utils.proton': _proton_mock}):
    import gamemodules.medievalengineersserver as mod
    from server import ServerError


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27016, dir=str(tmp_path))
    assert server.data['port'] == 27016
    assert server.data["servername"] == "AlphaGSM testserver"
    assert server.data["worldname"] == "testserver"
    assert server.data["maxplayers"] == mod.DEFAULT_MAX_PLAYERS


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27016
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27017", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer64/MedievalEngineersDedicated.exe"
    server.data["Steam_AppID"] = 367970
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 367970
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 367970
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 367970
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
    server.data["exe_name"] = "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path = tmp_path / "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "MedievalEngineersDedicated.exe",
        "console",
        "path",
        os.path.abspath(str(tmp_path / "instance-data")),
        "port",
        "27015",
    ]
    assert cwd == str(tmp_path / "DedicatedServer64")
    assert (tmp_path / "instance-data").is_dir()


def test_get_start_command_prefers_proton_on_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    wrap_mock = MagicMock(return_value=["proton", "run", "DedicatedServer64/MedievalEngineersDedicated.exe"])
    monkeypatch.setattr(mod.proton, "wrap_command", wrap_mock)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path = tmp_path / "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015

    mod.get_start_command(server)

    wrap_mock.assert_called_with(
        [
            "MedievalEngineersDedicated.exe",
            "console",
            "path",
            "Z:" + str((tmp_path / "instance-data").resolve()).replace("/", "\\"),
            "port",
            "27015",
        ],
        wineprefix=None,
        prefer_proton=True,
    )


def test_get_start_command_adds_virtual_display_on_linux(tmp_path, monkeypatch):
    assignments = {}
    monkeypatch.setattr(mod, "IS_LINUX", True)
    shared_wrapper = [
        "env",
        "-u",
        "TMPDIR",
        "-u",
        "TMP",
        "-u",
        "TEMP",
        "proton",
        "run",
        "MedievalEngineersDedicated.exe",
    ]
    monkeypatch.setattr(mod.proton, "wrap_command", lambda *args, **kwargs: list(shared_wrapper))
    display_wrapper = [
        "env",
        "-u",
        "TMPDIR",
        "-u",
        "TMP",
        "-u",
        "TEMP",
        "SDL_VIDEODRIVER=x11",
        "SDL_AUDIODRIVER=dummy",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "proton",
        "run",
        "MedievalEngineersDedicated.exe",
    ]
    monkeypatch.setattr(
        mod.proton,
        "prepend_env_assignments",
        lambda command, **kwargs: assignments.update(kwargs) or list(display_wrapper),
    )
    monkeypatch.setattr(mod.shutil, "which", lambda command: f"/usr/bin/{command}")
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path = tmp_path / "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015

    cmd, _cwd = mod.get_start_command(server)

    assert cmd == [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        *display_wrapper,
    ]
    assert assignments["WINEDLLOVERRIDES"] == ""


def test_wrap_linux_command_replaces_headless_wine_driver_override(monkeypatch):
    monkeypatch.setattr(mod.shutil, "which", lambda command: f"/usr/bin/{command}")
    monkeypatch.setattr(
        mod.proton,
        "wrap_command",
        lambda *args, **kwargs: [
            "env",
            "DISPLAY=",
            "WINEDLLOVERRIDES=winex11.drv=",
            "proton",
            "run",
            "MedievalEngineersDedicated.exe",
        ],
    )
    monkeypatch.setattr(
        mod.proton,
        "prepend_env_assignments",
        lambda command, **kwargs: [
            "env",
            *(f"{key}={value}" for key, value in kwargs.items()),
            *list(command)[1:],
        ],
    )

    command = mod._wrap_linux_command(["MedievalEngineersDedicated.exe"])

    assert "DISPLAY=" not in command
    assert "WINEDLLOVERRIDES=winex11.drv=" not in command
    assert command.count("WINEDLLOVERRIDES=") == 1


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_do_stop():
    server = DummyServer()
    with patch.object(mod.runtime_module, "send_to_server") as mocked_send:
        mod.do_stop(server, 0)
    mocked_send.assert_called_with(server, "\003")


def test_sync_server_config_writes_dedicated_cfg(tmp_path):
    server = DummyServer(name="meit")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 27016
    server.data["servername"] = "AlphaGSM Medieval"
    server.data["worldname"] = "MedievalWorld"
    server.data["maxplayers"] = "12"

    mod.sync_server_config(server)

    config_path = tmp_path / "instance-data" / mod.DEDICATED_CONFIG_NAME
    assert config_path.is_file()

    root = ET.parse(config_path).getroot()
    assert root.tag.endswith("MyConfigDedicated")
    assert root.findtext("ServerPort") == "27016"
    assert root.findtext("SteamPort") == "27017"
    assert root.findtext("ServerName") == "AlphaGSM Medieval"
    assert root.findtext("WorldName") == "MedievalWorld"
    assert root.findtext("IgnoreLastSession") == "false"
    assert root.findtext("RemoteApiEnabled") == "false"
    assert root.find("Scenario").attrib["Subtype"] == mod.DEFAULT_SCENARIO
    assert root.find("SessionSettings/MaxPlayers").text == "12"


def test_prestart_syncs_server_config(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 27016

    mod.prestart(server)

    assert (tmp_path / "instance-data" / mod.DEDICATED_CONFIG_NAME).is_file()


def test_runtime_requirements_enable_xvfb_container_env():
    server = DummyServer()
    server.data["dir"] = "/srv/me/"
    server.data["port"] = 27015

    requirements = mod.get_runtime_requirements(server)

    assert requirements["env"]["ALPHAGSM_PREFER_PROTON"] == "1"
    assert requirements["env"]["ALPHAGSM_XVFB"] == "1"
    assert requirements["env"]["SDL_VIDEODRIVER"] == "x11"
    assert requirements["env"]["LIBGL_ALWAYS_SOFTWARE"] == "1"


def test_container_spec_prefers_proton_runtime(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path = tmp_path / "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 27015

    spec = mod.get_container_spec(server)

    assert spec["env"]["ALPHAGSM_PREFER_PROTON"] == "1"


def test_instance_data_path_uses_windows_style_on_linux(tmp_path, monkeypatch):
    monkeypatch.setattr(mod, "IS_LINUX", True)
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"

    assert mod._instance_data_path(server) == "Z:" + str(
        (tmp_path / "instance-data").resolve()
    ).replace("/", "\\")


def test_container_spec_uses_dedicated_server_working_dir(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 27015
    server.data["exe_name"] = "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path = tmp_path / "DedicatedServer64/MedievalEngineersDedicated.exe"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == mod.CONTAINER_WORKING_DIR


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


def test_checkvalue_exe_name():
    server = DummyServer()
    result = mod.checkvalue(server, ("exe_name",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    result = mod.checkvalue(server, ("dir",), "/test/value")
    assert result == "/test/value"


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "AlphaGSM Medieval")
    assert result == "AlphaGSM Medieval"


def test_checkvalue_worldname():
    server = DummyServer()
    result = mod.checkvalue(server, ("worldname",), "World01")
    assert result == "World01"


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12")
    assert result == 12


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
