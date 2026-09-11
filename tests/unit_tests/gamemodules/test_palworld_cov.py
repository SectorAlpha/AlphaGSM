"""Full coverage tests for palworld."""

import os
import sys
from unittest.mock import patch, MagicMock

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.palworld', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.palworld as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=8211, dir=str(tmp_path))
    assert server.data['port'] == 8211


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 8211
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["publiclobby"] = True
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["8212", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["Steam_AppID"] = 2394010
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2394010
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2394010
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2394010
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
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    (tmp_path / "PalServer.sh").write_text("")
    binary = tmp_path / "Pal" / "Binaries" / "Linux"
    binary.mkdir(parents=True)
    (binary / "PalServer-Linux-Shipping").write_text("")
    server.data["publiclobby"] = True
    cmd, cwd = mod.get_start_command(server)
    assert isinstance(cmd, list)
    assert cwd == str(tmp_path)
    assert cmd[0] == "./PalServer.sh"
    assert "-port=8211" in cmd
    assert all(not arg.startswith("-queryport=") for arg in cmd)


def test_get_start_command_uses_nested_palserver_root(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "PalServer"
    (nested_root / "PalServer.sh").parent.mkdir(parents=True, exist_ok=True)
    (nested_root / "PalServer.sh").write_text("")
    (nested_root / "Pal" / "Binaries" / "Linux").mkdir(parents=True)
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    (nested_root / "Pal" / "Binaries" / "Linux" / "PalServer-Linux-Shipping").write_text("")
    server.data["publiclobby"] = True

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./Pal/Binaries/Linux/PalServer-Linux-Shipping"
    assert cwd == str(nested_root)


def test_get_start_command_prefers_install_root_wrapper_over_nested_root(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "PalServer"
    (nested_root / "PalServer.sh").parent.mkdir(parents=True, exist_ok=True)
    (nested_root / "PalServer.sh").write_text("")
    (nested_root / "Pal" / "Binaries" / "Linux").mkdir(parents=True)
    (nested_root / "Pal" / "Binaries" / "Linux" / "PalServer-Linux-Shipping").write_text("")
    (tmp_path / "PalServer.sh").write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    server.data["publiclobby"] = True

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./PalServer.sh"
    assert cwd == str(tmp_path)


def test_get_start_command_uses_resolved_root_for_docker_runtime(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "PalServer"
    (nested_root / "PalServer.sh").parent.mkdir(parents=True, exist_ok=True)
    (nested_root / "PalServer.sh").write_text("")
    (nested_root / "Pal" / "Binaries" / "Linux").mkdir(parents=True)
    (nested_root / "Pal" / "Binaries" / "Linux" / "PalServer-Linux-Shipping").write_text("")
    (tmp_path / "PalServer.sh").write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    server.data["runtime"] = "docker"
    server.data["publiclobby"] = True

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./Pal/Binaries/Linux/PalServer-Linux-Shipping"
    assert cwd == str(nested_root)


def test_get_start_command_finds_recursive_nested_palserver_root(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "steamapps" / "common" / "PalServer Dedicated" / "PalServer"
    (nested_root / "PalServer.sh").parent.mkdir(parents=True, exist_ok=True)
    (nested_root / "PalServer.sh").write_text("")
    (nested_root / "Pal" / "Binaries" / "Linux").mkdir(parents=True)
    (nested_root / "Pal" / "Binaries" / "Linux" / "PalServer-Linux-Shipping").write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    server.data["publiclobby"] = True

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./Pal/Binaries/Linux/PalServer-Linux-Shipping"
    assert cwd == str(nested_root)


def test_get_start_command_prefers_wrapper_over_linux_shipping_binary(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    server.data["publiclobby"] = True
    (tmp_path / "PalServer.sh").write_text("")
    binary = tmp_path / "Pal" / "Binaries" / "Linux"
    binary.mkdir(parents=True)
    (binary / "PalServer-Linux-Shipping").write_text("")

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./PalServer.sh"
    assert cwd == str(tmp_path)


def test_get_start_command_uses_custom_relative_executable_from_install_root(tmp_path):
    server = DummyServer()
    custom_wrapper = tmp_path / "scripts" / "PalServer.sh"
    custom_wrapper.parent.mkdir(parents=True)
    custom_wrapper.write_text("")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "scripts/PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015

    cmd, cwd = mod.get_start_command(server)

    assert cmd[0] == "./scripts/PalServer.sh"
    assert cwd == str(tmp_path)


def test_get_container_spec_maps_nested_palserver_workdir(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "PalServer"
    (nested_root / "PalServer.sh").parent.mkdir(parents=True, exist_ok=True)
    (nested_root / "PalServer.sh").write_text("")
    (nested_root / "Pal" / "Binaries" / "Linux").mkdir(parents=True)
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "PalServer.sh"
    server.data["port"] = 8211
    server.data["queryport"] = 27015
    server.data["runtime"] = "docker"
    (nested_root / "Pal" / "Binaries" / "Linux" / "PalServer-Linux-Shipping").write_text("")

    spec = mod.get_container_spec(server)

    assert spec["working_dir"] == "/srv/server/PalServer"
    assert spec["command"][0] == "./Pal/Binaries/Linux/PalServer-Linux-Shipping"
    assert spec["ports"] == [
        {"host": 8211, "container": 8211, "protocol": "udp"},
    ]


def test_query_and_info_use_runtime_resolved_main_udp_port():
    server = DummyServer()
    server.data["port"] = 8211
    server.data["queryport"] = 27015

    with patch.object(
        mod.runtime_module,
        "resolve_query_host",
        side_effect=["172.18.0.9", "172.18.0.9"],
    ) as resolve_query_host:
        assert mod.get_query_address(server) == ("172.18.0.9", 8211, "udp")
        assert mod.get_info_address(server) == ("172.18.0.9", 8211, "udp")

    assert resolve_query_host.call_args_list == [((server,),), ((server,),)]


def test_settings_paths_follow_nested_palserver_root(tmp_path):
    server = DummyServer()
    nested_root = tmp_path / "steamapps" / "common" / "PalServer"
    nested_root.mkdir(parents=True)
    (nested_root / "PalServer.sh").write_text("")
    server.data["dir"] = str(tmp_path)
    server.data["exe_name"] = "PalServer.sh"

    default_settings, active_settings = mod._settings_paths(server)

    assert default_settings == str(nested_root / "DefaultPalWorldSettings.ini")
    assert active_settings == str(
        nested_root / "Pal" / "Saved" / "Config" / "LinuxServer" / "PalWorldSettings.ini"
    )


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["publiclobby"] = True
    with pytest.raises(ServerError):
        mod.get_start_command(server)


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


def test_checkvalue_publiclobby():
    server = DummyServer()
    result = mod.checkvalue(server, ("publiclobby",), "true")
    assert result is True


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {"profiles": {"default": {"targets": ["saves"]}}, "schedule": [("default", 0, "days")]}
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
