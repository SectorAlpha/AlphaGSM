"""Full coverage tests for thefrontserver."""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from tests.unit_tests.gamemodules.helpers import DummyServer

sys.modules.pop('gamemodules.thefrontserver', None)
with patch.dict('sys.modules', {'screen': MagicMock(), 'utils.backups': MagicMock(), 'utils.backups.backups': MagicMock(), 'utils.steamcmd': MagicMock()}):
    import gamemodules.thefrontserver as mod
    from server import ServerError
    mod.runtime_module.send_to_server = MagicMock()


def test_configure_basic(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=7777, dir=str(tmp_path))
    assert server.data['port'] == 7777
    assert server.data['queryport'] == '7779'


def test_configure_ask_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt: "")
    server = DummyServer()
    server.data["port"] = 7777
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = "test"
    server.data["Steam_anonymous_login_possible"] = "test"
    server.data["maxplayers"] = 27015
    server.data["queryport"] = 27015
    server.data["servername"] = "test"
    server.data["worldname"] = "test"
    mod.configure(server, ask=True)


def test_configure_ask_custom(tmp_path, monkeypatch):
    inputs = iter(["7778", str(tmp_path / 'custom')])
    monkeypatch.setattr("builtins.input", lambda prompt: next(inputs))
    server = DummyServer()
    mod.configure(server, ask=True)


def test_configure_queryport_follows_selected_port(tmp_path):
    server = DummyServer()
    mod.configure(server, ask=False, port=9000, dir=str(tmp_path))
    assert server.data['queryport'] == '9002'


def test_install(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "ProjectWar/Binaries/Linux/TheFrontServer"
    server.data["Steam_AppID"] = 2334200
    server.data["Steam_anonymous_login_possible"] = True
    mod.install(server)


def test_update_with_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2334200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=True, restart=True)
    assert server._stopped
    assert server._started


def test_update_no_restart(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2334200
    server.data["Steam_anonymous_login_possible"] = True
    mod.update(server, validate=False, restart=False)
    assert server._stopped
    assert not server._started


def test_update_stop_exception(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["Steam_AppID"] = 2334200
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
    server.data["exe_name"] = "ProjectWar/Binaries/Linux/TheFrontServer"
    exe_path = tmp_path / "ProjectWar/Binaries/Linux/TheFrontServer"
    exe_path.parent.mkdir(parents=True, exist_ok=True)
    exe_path.write_text("")
    server.data["port"] = 7777
    server.data["queryport"] = 7779
    server.data["maxplayers"] = 32
    server.data["servername"] = "AlphaGSM Test Front"
    cmd, cwd = mod.get_start_command(server)
    assert cmd == [
        "./ProjectWar/Binaries/Linux/TheFrontServer",
        "ProjectWar",
        "ProjectWar_Start?Listen?MaxPlayers=32",
        "-server",
        "-game",
        "-QueueThreshold=32",
        "-ServerName=AlphaGSM Test Front",
        "-log",
        "-locallogtimes",
        "-EnableParallelCharacterMovementTickFunction",
        "-EnableParallelCharacterTickFunction",
        "-UseDynamicPhysicsScene",
        "-port=7777",
        "-BeaconPort=7778",
        "-QueryPort=7779",
        "-Game.PhysicsVehicle=false",
        "-ansimalloc",
        "-Game.MaxFrameRate=35",
        "-ShutDownServicePort=7780",
    ]
    assert cwd == server.data["dir"]


def test_setting_schema_exposes_thefront_launch_formats():
    assert mod.setting_schema["port"].launch_arg_format == "-port={value}"
    assert mod.setting_schema["queryport"].launch_arg_format == "-QueryPort={value}"


def test_get_start_command_missing_exe(tmp_path):
    server = DummyServer()
    server.data["dir"] = str(tmp_path) + "/"
    server.data["exe_name"] = "nonexistent"
    server.data["port"] = 27015
    server.data["queryport"] = 27015
    with pytest.raises(ServerError):
        mod.get_start_command(server)


def test_runtime_wrappers_opt_into_host_user_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(mod.runtime_module, "_steamcmd_sdk_mounts", lambda *args, **kwargs: [])
    server = DummyServer()
    server.data.update(
        {
            "dir": str(tmp_path),
            "exe_name": "ProjectWar/Binaries/Linux/TheFrontServer",
            "port": 7777,
            "queryport": 7779,
        }
    )
    executable = tmp_path / server.data["exe_name"]
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")

    requirements = mod.get_runtime_requirements(server)
    spec = mod.get_container_spec(server)

    assert requirements["run_as_host_user"] is True
    assert requirements["container_home"] == "/home/alphagsm"
    assert requirements["env"]["HOME"] == "/home/alphagsm"
    assert spec["run_as_host_user"] is True
    assert spec["container_home"] == "/home/alphagsm"
    assert spec["env"]["HOME"] == "/home/alphagsm"
    assert spec["command"][0] == "./ProjectWar/Binaries/Linux/TheFrontServer"


def test_runtime_start_reuses_one_manager_mount_snapshot(tmp_path, monkeypatch):
    manager_root = tmp_path / "manager"
    manager_root.mkdir(mode=0o700)
    install_dir = manager_root / "servers" / "front"
    executable = install_dir / "ProjectWar/Binaries/Linux/TheFrontServer"
    executable.parent.mkdir(parents=True)
    executable.write_text("", encoding="utf-8")
    monkeypatch.setenv("ALPHAGSM_HOME", str(manager_root))

    server = DummyServer(name="front")
    server.module = mod
    server.data.update(
        {
            "runtime": "docker",
            "dir": str(install_dir),
            "exe_name": "ProjectWar/Binaries/Linux/TheFrontServer",
            "port": 7777,
            "queryport": 7779,
            "maxplayers": 32,
            "servername": "AlphaGSM Front",
        }
    )
    discovery_calls = []

    def _discover_mounts():
        discovery_calls.append(True)
        if len(discovery_calls) == 1:
            return [
                {
                    "source": "/host/alphagsm",
                    "destination": str(manager_root),
                },
                {
                    "source": "/host/steam",
                    "destination": "/home/cosmosquark/Steam",
                },
            ]
        return []

    runtime_module = importlib.import_module("server.runtime")
    runtime = runtime_module.ContainerRuntime()
    observed = []
    monkeypatch.setattr(runtime_module, "_get_configured_runtime_name", lambda: "docker")
    monkeypatch.setattr(runtime_module, "_running_inside_container", lambda: True)
    monkeypatch.setattr(runtime_module, "_current_container_bind_mounts", _discover_mounts)
    monkeypatch.setattr(runtime, "_ensure_runtime_image_available", lambda spec: None)
    monkeypatch.setattr(runtime, "_container_running_state", lambda name: None)
    monkeypatch.setattr(
        runtime,
        "_run_check_output",
        lambda command, text=False: observed.append(command) or ("linux" if command[:2] == ["docker", "info"] else "ok"),
    )

    runtime.start(server)

    assert discovery_calls == [True]
    docker_command = observed[-1]
    assert "/host/alphagsm/servers/front:/srv/server:rw" in docker_command
    assert "/host/alphagsm/runtime/front/home:/home/alphagsm:rw" in docker_command


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


def test_checkvalue_queryport():
    server = DummyServer()
    result = mod.checkvalue(server, ("queryport",), "12345")
    assert result == 12345


def test_checkvalue_maxplayers():
    server = DummyServer()
    result = mod.checkvalue(server, ("maxplayers",), "12345")
    assert result == 12345


def test_checkvalue_servername():
    server = DummyServer()
    result = mod.checkvalue(server, ("servername",), "/test/value")
    assert result == "/test/value"


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
