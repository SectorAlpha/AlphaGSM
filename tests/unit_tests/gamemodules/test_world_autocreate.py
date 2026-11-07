"""Interactive world selection and explicit unattended startup contracts."""

from importlib import import_module
from pathlib import Path
from types import SimpleNamespace

import pytest

from server import ServerError
from utils.cmdparse.cmdparse import parse


@pytest.fixture(params=["terraria", "terraria.vanilla", "terraria.tshock", "necserver"])
def world_server(request, tmp_path):
    module = import_module("gamemodules." + request.param)
    executable = "Server.jar" if request.param == "necserver" else "Server"
    (tmp_path / executable).touch()
    server = SimpleNamespace(name="example", data={
        "dir": str(tmp_path), "exe_name": executable, "port": 7777,
        "world": "my world.wld" if request.param != "necserver" else "my world",
        "worldname": "My World", "worldsize": "1", "maxplayers": "8",
        "javapath": "java", "slots": "10", "datadir": str(tmp_path),
    })
    return module, server


@pytest.mark.parametrize("existing_world", [False, True])
def test_plain_start_leaves_world_selection_to_console(world_server, existing_world, tmp_path):
    module, server = world_server
    if existing_world:
        directory = tmp_path / ("saves" if module.__name__.endswith("necserver") else "Worlds")
        directory.mkdir()
        (directory / server.data["world"]).write_text("existing world")

    command, _ = module.get_start_command(server)
    spec = module.get_container_spec(server)

    for args in (command, spec["command"]):
        assert "-world" not in args
        assert "-autocreate" not in args
        assert "-worldname" not in args


@pytest.mark.parametrize("runtime", ["process", "docker"])
def test_cli_autocreate_reaches_process_and_docker_launch(world_server, runtime):
    module, server = world_server
    server.data["runtime"] = runtime
    before = dict(server.data)
    args, options = parse(["--autocreate"], module.command_args["start"])

    command, _ = module.get_start_command(server, *args, **options)
    spec = module.get_container_spec(server, *args, **options)

    expected_world = server.data["world"]
    if not module.__name__.endswith("necserver"):
        expected_world = "Worlds/" + expected_world
    for launch in (command, spec["command"]):
        assert launch[launch.index("-world") + 1] == expected_world
        if not module.__name__.endswith("necserver"):
            assert launch[launch.index("-autocreate") + 1] == "1"
            assert launch[launch.index("-worldname") + 1] == "My World"
    assert server.data == before
    assert "-world" not in module.get_start_command(server)[0]


@pytest.mark.parametrize("runtime", ["process", "docker"])
def test_autocreate_is_noop_when_world_exists(world_server, runtime, tmp_path):
    module, server = world_server
    server.data["runtime"] = runtime
    directory = tmp_path / ("saves" if module.__name__.endswith("necserver") else "Worlds")
    directory.mkdir()
    world = directory / server.data["world"]
    world.write_bytes(b"existing world data")

    command, _ = module.get_start_command(server, autocreate=True)
    spec = module.get_container_spec(server, autocreate=True)

    for launch in (command, spec["command"]):
        assert "-world" not in launch
        assert "-autocreate" not in launch
        assert "-worldname" not in launch
    assert (command, _) == module.get_start_command(server)
    assert spec == module.get_container_spec(server)
    assert world.read_bytes() == b"existing world data"


def test_necesse_autocreate_requires_known_save_location(tmp_path):
    module = import_module("gamemodules.necserver")
    (tmp_path / "Server.jar").touch()
    server = SimpleNamespace(name="legacy", data={
        "dir": str(tmp_path), "exe_name": "Server.jar", "javapath": "java",
        "world": "legacy", "port": 14159, "slots": 10,
    })
    with pytest.raises(ServerError, match="datadir"):
        module.get_start_command(server, autocreate=True)
    assert "-datadir" not in module.get_start_command(server)[0]


@pytest.mark.parametrize("save_path", ["saves/my world.zip", "saves/worlds/my world.zip"])
def test_necesse_autocreate_leaves_existing_zip_save_alone(tmp_path, save_path):
    module = import_module("gamemodules.necserver")
    (tmp_path / "Server.jar").touch()
    world = tmp_path / save_path
    world.parent.mkdir(parents=True)
    world.write_bytes(b"existing save")
    server = SimpleNamespace(name="example", data={
        "dir": str(tmp_path), "datadir": str(tmp_path), "exe_name": "Server.jar",
        "javapath": "java", "world": "my world", "port": 14159, "slots": 10,
    })
    assert module.get_start_command(server, autocreate=True) == module.get_start_command(server)
    assert world.read_bytes() == b"existing save"


@pytest.mark.parametrize("datadir", ["data", "external"])
def test_necesse_datadir_resolves_existing_save_and_docker_mount(tmp_path, datadir):
    module = import_module("gamemodules.necserver")
    install = tmp_path / "server"
    install.mkdir()
    (install / "Server.jar").touch()
    data_path = install / "data" if datadir == "data" else tmp_path / "external"
    (data_path / "saves").mkdir(parents=True)
    (data_path / "saves" / "example.zip").write_bytes(b"existing world")
    server = SimpleNamespace(name="example", data={
        "dir": str(install), "datadir": "data" if datadir == "data" else str(data_path),
        "exe_name": "Server.jar", "javapath": "java", "world": "example",
        "port": 14159, "slots": 10,
    })
    assert module.get_start_command(server, autocreate=True) == module.get_start_command(server)
    spec = module.get_container_spec(server, autocreate=True)
    container_data = spec["command"][spec["command"].index("-datadir") + 1]
    assert container_data == "/srv/necesse-data"
    assert any(mount["source"] == str(data_path) and mount["target"] == container_data
               for mount in spec["mounts"])


@pytest.mark.parametrize("legacy", [False, True])
def test_necesse_setup_assigns_local_datadir_only_to_new_installations(tmp_path, legacy):
    from tests.unit_tests.gamemodules.helpers import DummyServer

    module = import_module("gamemodules.necserver")
    server = DummyServer()
    server.data["world"] = "chosen-before-setup"
    if legacy:
        server.data["Steam_AppID"] = 1169370
        server.data["dir"] = str(tmp_path)
    module.configure(server, ask=False, dir=str(tmp_path))
    if legacy:
        assert "datadir" not in server.data
    else:
        assert Path(server.data["datadir"]) == tmp_path


def test_necesse_worlds_directory_is_not_mistaken_for_existing_world(tmp_path):
    module = import_module("gamemodules.necserver")
    (tmp_path / "Server.jar").touch()
    (tmp_path / "saves" / "worlds").mkdir(parents=True)
    (tmp_path / "saves" / "worlds" / "other.zip").write_text("other")
    server = SimpleNamespace(name="example", data={
        "dir": str(tmp_path), "datadir": str(tmp_path), "exe_name": "Server.jar",
        "javapath": "java", "world": "worlds", "port": 14159, "slots": 10,
    })
    command, _ = module.get_start_command(server, autocreate=True)
    assert command[command.index("-world") + 1] == "worlds"
