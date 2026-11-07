"""Optional native ARK RCON supports actual engine-object verification."""
from importlib import import_module

import pytest

from server import ServerError
from tests.unit_tests.gamemodules.helpers import DummyServer


def prepared(tmp_path):
    """Configure a tiny native launch fixture."""
    module = import_module("gamemodules.ark")
    server = DummyServer("arknative")
    module.configure(server, ask=False, port=28121, dir=str(tmp_path))
    executable = tmp_path / server.data["exe_name"]
    executable.parent.mkdir(parents=True)
    executable.write_text("")
    return module, server


def test_rcon_remains_disabled_until_explicitly_enabled_with_private_password(tmp_path):
    module, server = prepared(tmp_path)
    command, _directory = module.get_start_command(server)
    assert "?RCONEnabled=" not in command[1]
    with pytest.raises(ServerError, match="password"):
        module.checkvalue(server, ["rconenabled"], "true")
    server.data["adminpassword"] = "generated-local-password"
    server.data["rconenabled"] = module.checkvalue(server, ["rconenabled"], "true")
    server.data["rconport"] = module.checkvalue(server, ["rconport"], "28312")
    command, _directory = module.get_start_command(server)
    assert "?RCONEnabled=True?RCONPort=28312" in command[1]
    assert {"-stdout", "-FullStdOutLogOutput", "-forcelogflush"}.issubset(command)
    assert any(item["key"] == "rconport" and item["protocol"] == "tcp"
               for item in module.port_claim_definitions)
    assert any(item["host"] == 28312 and item["protocol"] == "tcp"
               for item in module.get_runtime_requirements(server)["ports"])


def test_false_rcon_value_and_bad_boolean_never_enable_listener(tmp_path):
    module, server = prepared(tmp_path)
    server.data["rconenabled"] = module.checkvalue(server, ["rconenabled"], "false")
    command, _directory = module.get_start_command(server)
    assert "?RCONEnabled=" not in command[1]
    with pytest.raises(ServerError):
        module.checkvalue(server, ["rconenabled"], "maybe")


def test_live_command_builders_use_saved_mod_snapshot_without_reading_native_ini(tmp_path, monkeypatch):
    """Engine-private INIs must not prevent Docker console, status or stop lookup."""
    module, server = prepared(tmp_path)
    adapter = import_module("gamemodules.ark.workshop")
    server.data["mods"] = {"ark_workshop_launch_ids": ["999", "111"]}
    def private_ini(_path):
        raise PermissionError("engine owns a private native INI")
    monkeypatch.setattr(adapter, "_metadata", private_ini)
    command, _directory = module.get_start_command(server)
    assert "?GameModIds=999,111" in command[1]
    spec = module.get_container_spec(server)
    assert "?GameModIds=999,111" in spec["command"][1]


def test_docker_uses_host_identity_and_private_home_without_permission_rewrites(tmp_path, monkeypatch):
    module, server = prepared(tmp_path)
    steam = tmp_path / "steamcmd/linux64"
    steam.mkdir(parents=True)
    (steam / "steamclient.so").write_bytes(b"runtime fixture")
    monkeypatch.setattr(module.steamcmd, "STEAMCMD_DIR", str(steam.parent))
    requirements = module.get_runtime_requirements(server)
    spec = module.get_container_spec(server)
    assert requirements["run_as_host_user"] is True and spec["run_as_host_user"] is True
    assert spec["env"]["HOME"] == "/home/alphagsm"
    assert any(mount["target"] == "/home/alphagsm/.steam/sdk64" and mount["mode"] == "ro"
               for mount in spec["mounts"])
    assert spec["command"][0] == "./ShooterGame/Binaries/Linux/ShooterGameServer"
    assert not any("chmod" in argument or "runuser" in argument for argument in spec["command"])


def test_staged_map_does_not_change_default_world_until_explicitly_selected(tmp_path):
    module, server = prepared(tmp_path)
    server.data["mods"] = {"ark_workshop_ids": ["111"], "ark_workshop_launch_ids": [],
                           "ark_workshop_maps": {"111": {"FlatMap": "/Game/Mods/111/FlatMap"}}}
    command, _directory = module.get_start_command(server)
    assert command[1].startswith("TheIsland?listen?") and "?MapModID=" not in command[1]
    server.data["map"] = "/Game/Mods/111/FlatMap"
    command, _directory = module.get_start_command(server)
    assert command[1].startswith("/Game/Mods/111/FlatMap?listen?")
    assert "?MapModID=111" in command[1] and "?GameModIds=" not in command[1]
    spec = module.get_container_spec(server)
    assert spec["command"][1] == command[1]


def test_prestart_snapshots_operator_mods_even_when_autoapply_is_disabled(tmp_path, monkeypatch):
    module, server = prepared(tmp_path)
    adapter = import_module("gamemodules.ark.workshop")
    config = tmp_path / adapter.CONFIG
    config.parent.mkdir(parents=True)
    config.write_text("[ServerSettings]\nActiveMods=999,888\n")
    module.ensure_mod_state(server)["autoapply"] = False
    module.prestart(server)
    assert server.data["mods"]["ark_workshop_launch_ids"] == ["999", "888"]
    monkeypatch.setattr(adapter, "_metadata", lambda _path: (_ for _ in ()).throw(PermissionError()))
    assert "?GameModIds=999,888" in module.get_start_command(server)[0][1]
