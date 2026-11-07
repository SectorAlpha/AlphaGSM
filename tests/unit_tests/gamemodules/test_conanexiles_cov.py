"""Full coverage tests for conanexiles."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop("gamemodules.conanexiles", None)
with patch.dict(
    "sys.modules",
    {
        "utils.backups": MagicMock(),
        "utils.backups.backups": MagicMock(),
        "utils.steamcmd": MagicMock(),
    },
):
    import gamemodules.conanexiles as mod
    from server import ServerError

    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data["port"] == 7777
    assert server.data["exe_name"] == (
        "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )


def test_configure_migrates_obsolete_windows_executable(tmp_path):
    server = DummyServer()
    server.data["exe_name"] = (
        "ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe"
    )

    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))

    assert server.data["exe_name"] == (
        "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 40
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / "custom")])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = (
        "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    with patch.object(mod.steamcmd, "download") as download:
        mod.install(server)

    assert download.call_args.kwargs["force_platform"] == "linux"
    assert "force_windows" not in download.call_args.kwargs


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 443030
    server.data["Steam_anonymous_login_possible"] = True
    server.stop = MagicMock(side_effect=Exception("already stopped"))
    mod.update(server, validate=False, restart=False)


def test_restart():
    server = DummyServer()
    mod.restart(server)
    assert server._stopped
    assert server._started


def test_sync_server_config(tmp_path):
    server = DummyServer("conan")
    server.data["dir"] = str(tmp_path) + "/"
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    server.data["maxplayers"] = 24
    server.data["servername"] = "AlphaGSM Conan"

    mod.sync_server_config(server)

    config_dir = tmp_path / "ConanSandbox" / "Saved" / "Config" / "LinuxServer"
    engine_text = (config_dir / "Engine.ini").read_text(encoding="utf-8")
    game_text = (config_dir / "Game.ini").read_text(encoding="utf-8")
    server_settings_text = (config_dir / "ServerSettings.ini").read_text(
        encoding="utf-8"
    )

    assert "Port=7777" in engine_text
    assert "GameServerQueryPort=27015" in engine_text
    assert "ServerName=AlphaGSM Conan" in engine_text
    assert "MaxPlayers=24" in game_text
    assert "[ServerSettings]" in server_settings_text


def test_sync_server_config_migrates_legacy_windows_files_and_database(tmp_path):
    server = DummyServer("conan")
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 7777,
            "queryport": 27015,
            "maxplayers": 24,
            "servername": "AlphaGSM Conan",
        }
    )
    saved_dir = tmp_path / "ConanSandbox" / "Saved"
    windows_dir = saved_dir / "Config" / "WindowsServer"
    windows_dir.mkdir(parents=True)
    (windows_dir / "Engine.ini").write_text(
        "[OnlineSubsystem]\nServerPassword=preserved\n", encoding="utf-8"
    )
    (saved_dir / "Game.db").write_text("world", encoding="utf-8")

    mod.sync_server_config(server)

    linux_dir = saved_dir / "Config" / "LinuxServer"
    assert "ServerPassword=preserved" in (linux_dir / "Engine.ini").read_text(
        encoding="utf-8"
    )
    assert (saved_dir / "game.db").read_text(encoding="utf-8") == "world"
    assert not (saved_dir / "Game.db").exists()


def test_sync_server_config_no_dir_is_noop():
    server = DummyServer()
    server.data["servername"] = "AlphaGSM Conan"
    mod.sync_server_config(server)


def test_get_start_command_prefers_shipping_executable(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = (
        tmp_path
        / "ConanSandbox"
        / "Binaries"
        / "Linux"
        / "ConanSandboxServer-Linux-Shipping"
    )
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = (
        "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 16
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping",
        "ConanSandbox",
        "-log",
        "-console",
        "-Port=7777",
        "-QueryPort=27015",
        "-MaxPlayers=16",
    ]
    assert cwd == server.data["dir"]


def test_get_start_command_accepts_native_wrapper_fallback(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    exe = tmp_path / "ConanSandboxServer.sh"
    exe.write_text("")
    server.data["exe_name"] = "ConanSandboxServer.sh"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 16
    server.data["port"] = 7777
    server.data["queryport"] = 27015
    cmd, _cwd = mod.get_start_command(server)
    assert cmd[0] == "./ConanSandboxServer.sh"


def test_get_start_command_ignores_retained_legacy_windows_executable(tmp_path):
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "exe_name": (
                "ConanSandbox/Binaries/Win64/"
                "ConanSandboxServer-Win64-Shipping.exe"
            ),
            "map": "ConanSandbox",
            "maxplayers": 16,
            "port": 7777,
            "queryport": 27015,
        }
    )
    windows = tmp_path / server.data["exe_name"]
    windows.parent.mkdir(parents=True)
    windows.write_text("")
    native = (
        tmp_path
        / "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )
    native.parent.mkdir(parents=True)
    native.write_text("")

    command, _cwd = mod.get_start_command(server)

    assert command[0] == (
        "./ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )


def test_port_claims_derive_pinger_from_current_or_overridden_game_port(tmp_path):
    from server.port_manager import collect_claim_set

    server = DummyServer("conan")
    server.module = mod
    server.data.update(
        {
            "dir": str(tmp_path) + "/",
            "port": 19000,
            "pingerport": 18001,
            "queryport": 27015,
            "runtime": {"backend": "process"},
        }
    )

    claims = collect_claim_set(server)
    overridden = collect_claim_set(server, overrides={"port": 20000})

    assert 19001 in {endpoint.port for endpoint in claims.endpoints}
    assert 18001 not in {endpoint.port for endpoint in claims.endpoints}
    assert 20001 in {endpoint.port for endpoint in overridden.endpoints}
    assert 19001 not in {endpoint.port for endpoint in overridden.endpoints}


def test_runtime_contract_uses_native_steamcmd_linux_family(tmp_path):
    server = DummyServer("conan")
    server.data.update(
        {"dir": str(tmp_path) + "/", "port": 7777, "queryport": 27015}
    )
    exe = (
        tmp_path
        / "ConanSandbox"
        / "Binaries"
        / "Linux"
        / "ConanSandboxServer-Linux-Shipping"
    )
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    server.data["exe_name"] = (
        "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
    )

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["family"] == "steamcmd-linux"
    assert requirements["run_as_host_user"] is True
    assert requirements["container_home"] == "/home/alphagsm"
    assert spec["command"][0].endswith("ConanSandboxServer-Linux-Shipping")
    assert spec["run_as_host_user"] is True
    assert spec["container_home"] == "/home/alphagsm"


def test_setting_schema_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-Port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"
    assert mod.setting_schema["maxplayers"].launch_arg_format == "-MaxPlayers={value}"


def test_get_query_and_info_address():
    server = DummyServer()
    server.data["queryport"] = 27015
    expected = ("127.0.0.1", 27015, "a2s")
    with patch.object(mod.runtime_module, "resolve_query_host", return_value="127.0.0.1"):
        assert mod.get_query_address(server) == expected
        assert mod.get_info_address(server) == expected


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["map"] = "ConanSandbox"
    server.data["maxplayers"] = 16
    server.data["port"] = 7777
    server.data["queryport"] = 27015
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
    assert mod.checkvalue(server, ("port",), "12345") == 12345


def test_checkvalue_queryport():
    server = DummyServer()
    assert mod.checkvalue(server, ("queryport",), "27015") == 27015


def test_checkvalue_maxplayers():
    server = DummyServer()
    assert mod.checkvalue(server, ("maxplayers",), "70") == 70


def test_checkvalue_map():
    server = DummyServer()
    assert mod.checkvalue(server, ("map",), "/Game/Maps/ConanSandbox") == "/Game/Maps/ConanSandbox"


def test_checkvalue_servername():
    server = DummyServer()
    assert mod.checkvalue(server, ("servername",), "AlphaGSM Conan") == "AlphaGSM Conan"


def test_checkvalue_exe_name():
    server = DummyServer()
    assert mod.checkvalue(server, ("exe_name",), "ConanSandboxServer.exe") == "ConanSandboxServer.exe"


def test_checkvalue_dir():
    server = DummyServer()
    assert mod.checkvalue(server, ("dir",), "/srv/conan/") == "/srv/conan/"


def test_checkvalue_backup():
    server = DummyServer()
    server.data["backup"] = {
        "profiles": {"default": {"targets": ["saves"]}},
        "schedule": [("default", 0, "days")],
    }
    mod.checkvalue(server, ("backup", "profiles", "default", "targets"), "newsave")
