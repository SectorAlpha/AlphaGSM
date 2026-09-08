"""Regression cases from the September 7 CI launch logs."""

from types import SimpleNamespace
from pathlib import Path

import pytest

from gamemodules.terraria import tshock
from utils.valve_server import define_valve_server_module
from utils.valve_server import _valve_launcher_candidates


@pytest.mark.parametrize("executable", ["TShock.Server", "TShock.Server.dll"])
@pytest.mark.parametrize("existing_world", [False, True])
def test_tshock_autocreate_selects_world_without_interactive_prompt(tmp_path, executable, existing_world):
    (tmp_path / executable).touch()
    worlds = tmp_path / "Worlds"
    worlds.mkdir()
    if existing_world:
        (worlds / "my world.wld").touch()
    server = SimpleNamespace(name="shock", data={
        "dir": str(tmp_path), "exe_name": executable, "port": 7777,
        "world": "my world.wld", "worldsize": "1", "worldname": "My World",
        "maxplayers": "8", "serverpassword": "private",
    })

    command, cwd = tshock.get_start_command(server, autocreate=True)

    if existing_world:
        assert "-autocreate" not in command
        assert "-worldname" not in command
    else:
        assert command[command.index("-world") + 1] == "Worlds/my world.wld"
        assert command[command.index("-autocreate") + 1] == "1"
        assert command[command.index("-worldname") + 1] == "My World"
    assert command[command.index("-maxplayers") + 1] == "8"
    assert command[command.index("-password") + 1] == "private"
    assert Path(cwd) == tmp_path
    spec = tshock.get_container_spec(server, autocreate=True)
    if existing_world:
        assert "-world" not in spec["command"]
        assert spec == tshock.get_container_spec(server)
    else:
        assert spec["command"][spec["command"].index("-world") + 1] == "Worlds/my world.wld"


@pytest.mark.parametrize("wrapper", ["srcds_run", "srcds_run_64"])
def test_source_keeps_wrapper_that_sets_library_search_path(tmp_path, wrapper):
    module = define_valve_server_module(
        game_name="Example", engine="source", steam_app_id=1,
        game_dir="example", executable="srcds_run", default_map="example", max_players=16,
    )
    (tmp_path / wrapper).touch()
    (tmp_path / "srcds_linux64").touch()
    server = SimpleNamespace(name="example", data={
        "dir": str(tmp_path), "exe_name": "srcds_run", "port": 27015,
        "startmap": "example", "server_cfg": "server.cfg", "maxplayers": 16,
    })

    command, cwd = module.get_start_command(server)

    assert command[0] == "./" + wrapper
    assert Path(cwd) == tmp_path


def test_source_keeps_explicit_launcher_override():
    candidates = _valve_launcher_candidates(
        engine="source", default_executable="srcds_run", configured_executable="custom-launcher",
    )
    assert candidates[0] == "custom-launcher"
    assert candidates.index("srcds_run") < candidates.index("srcds_linux64")


@pytest.mark.parametrize("configured", ["srcds_run", "srcds_run_64"])
def test_source_uses_own_launcher_before_mounted_game_content(tmp_path, configured):
    from gamemodules import gmodserver

    (tmp_path / "srcds_run").touch()
    content = tmp_path / "_gmod_content" / "tf"
    content.mkdir(parents=True)
    (content / "srcds_run_64").touch()
    server = SimpleNamespace(name="gmod", data={
        "dir": str(tmp_path), "exe_name": configured, "port": 27015,
        "startmap": "gm_construct", "server_cfg": "server.cfg", "maxplayers": 16,
    })

    command, cwd = gmodserver.get_start_command(server)

    assert command[0] == "./srcds_run"
    assert Path(cwd) == tmp_path
    spec = gmodserver.get_container_spec(server)
    assert spec["command"][0] == "./srcds_run"
    assert spec["working_dir"].rstrip("/") == "/srv/server"
