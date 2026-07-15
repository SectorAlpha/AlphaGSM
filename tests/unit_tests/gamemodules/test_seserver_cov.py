"""Full coverage tests for seserver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop("gamemodules.seserver", None)
with patch.dict(
    "sys.modules",
    {
        "screen": MagicMock(),
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.seserver as mod
    from server import ServerError

    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=27016, dir=str(tmp_path))
    assert server.data["port"] == 27016


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 27016
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["servername"] = "AlphaGSM se"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["27017", str(tmp_path / "custom")])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "DedicatedServer64/SpaceEngineersDedicated.exe"
    server.data["Steam_AppID"] = 298740
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 298740
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 298740
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 298740
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception("already stopped"))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_resolve_executable_name_falls_back_to_known_paths(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "DedicatedServer64" / "SpaceEngineersDedicated.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = "missing.exe"
    assert mod._resolve_executable_name(server) == "DedicatedServer64/SpaceEngineersDedicated.exe"


def test_get_start_command_windows(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "DedicatedServer64" / "SpaceEngineersDedicated.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = "DedicatedServer64/SpaceEngineersDedicated.exe"
    server.data["port"] = 27016
    with patch.object(mod, "IS_LINUX", False):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "SpaceEngineersDedicated.exe",
        "-console",
        "-path",
        str(tmp_path),
        "-port",
        "27016",
        "-start",
    ]
    assert cwd == str(tmp_path / "DedicatedServer64")


def test_get_start_command_linux_wraps_with_proton(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "DedicatedServer64" / "SpaceEngineersDedicated.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = "DedicatedServer64/SpaceEngineersDedicated.exe"
    server.data["port"] = 27016
    wrap_mock = MagicMock(return_value=["proton", "run", "SpaceEngineersDedicated.exe"])
    with patch.object(mod, "IS_LINUX", True), patch.object(mod.proton, "wrap_command", wrap_mock):
        cmd, cwd = mod.get_start_command(server)
    assert cmd == ["proton", "run", "SpaceEngineersDedicated.exe"]
    wrap_mock.assert_called_once()
    assert cwd == str(tmp_path / "DedicatedServer64")


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27016
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_get_query_and_info_address():
    server = DummyServer()
    server.data["port"] = 27016
    expected = ("127.0.0.1", 27016, "udp")
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected


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
    assert mod.checkvalue(server, ("port",), "27017") == 27017


def test_checkvalue_exe_name():
    server = DummyServer()
    assert mod.checkvalue(server, ("exe_name",), "/test/value") == "/test/value"


def test_checkvalue_dir():
    server = DummyServer()
    assert mod.checkvalue(server, ("dir",), "/test/value") == "/test/value"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {
        "profiles": {"default": {"targets": ["saves"]}},
        "schedule": [("default", 0, "days")],
    }
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")


def test_runtime_metadata_exposes_wine_proton_contract():
    server = DummyServer()
    server.data.update({"dir": "/srv/se", "port": 27016})
    runtime = mod.get_runtime_requirements(server)
    assert runtime["family"] == "wine-proton"
    assert any(port["container"] == 27016 and port["protocol"] == "udp" for port in runtime["ports"])


def test_container_spec_uses_dedicated_working_dir(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "DedicatedServer64" / "SpaceEngineersDedicated.exe"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = "DedicatedServer64/SpaceEngineersDedicated.exe"
    server.data["port"] = 27016
    spec = mod.get_container_spec(server)
    assert spec["working_dir"].endswith("/DedicatedServer64")
