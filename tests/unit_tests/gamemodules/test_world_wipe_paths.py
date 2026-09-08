"""Game-specific reset targets preserve configuration and unrelated worlds."""

from importlib import import_module
from types import SimpleNamespace

import pytest

from server import Server, ServerError
import server.runtime as runtime_module


@pytest.mark.parametrize("module_name,worlds", [
    ("minecraft", ["custom"]),
    ("minecraft.vanilla", ["custom"]),
    ("minecraft.paper", ["custom", "custom_nether", "custom_the_end"]),
    ("minecraft.bedrock", ["worlds/custom"]),
    ("terraria", ["Worlds/example.wld", "Worlds/example.wld.bak"]),
    ("terraria.vanilla", ["Worlds/example.wld"]),
    ("terraria.tshock", ["Worlds/example.wld", "Worlds/example.wld.bak2"]),
    ("necserver", ["saves/example.zip", "saves/worlds/example.zip"]),
    ("rust", ["server/my_server_identity/proceduralmap.1000.12345.999.map",
              "server/my_server_identity/proceduralmap.1000.12345.999.sav",
              "server/my_server_identity/proceduralmap.1000.12345.999.sav.1"]),
])
def test_world_reset_removes_only_game_owned_targets(tmp_path, monkeypatch, module_name, worlds):
    module = import_module("gamemodules." + module_name)
    server = SimpleNamespace(name="example", module=module, data={
        "dir": str(tmp_path), "datadir": str(tmp_path), "levelname": "stale",
        "world": "example" if module_name == "necserver" else "example.wld",
        "level": "Procedural Map", "seed": 12345, "worldsize": 1000,
    })
    keep = ["server.properties", "plugins/plugin.jar", "tshock/tshock.sqlite",
            "Worlds/another.wld", "other/level.dat", "saves/other.zip",
            "server/my_server_identity/cfg/server.cfg",
            "server/my_server_identity/player.blueprints.5.db",
            "server/my_server_identity/proceduralmap.2000.12345.999.sav",
            "server/other/proceduralmap.1000.12345.999.sav"]
    for name in keep:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("keep")
    (tmp_path / "server.properties").write_text("level-name=custom\n")
    for name in worlds:
        path = tmp_path / name
        if module_name.startswith("minecraft"):
            path.mkdir(parents=True)
            (path / "level.dat").write_text("world data")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("world data")
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)

    Server.wipe(server, yes=True)

    assert all(not (tmp_path / name).exists() for name in worlds)
    assert all((tmp_path / name).is_file() for name in keep)


def test_necesse_wipe_requires_known_local_data_directory(tmp_path, monkeypatch):
    module = import_module("gamemodules.necserver")
    server = SimpleNamespace(name="example", module=module,
                             data={"dir": str(tmp_path), "world": "example"})
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    with pytest.raises(ServerError, match="datadir"):
        Server.wipe(server, yes=True)


def test_rust_wipe_refuses_unsupported_map_type(tmp_path, monkeypatch):
    module = import_module("gamemodules.rust")
    server = SimpleNamespace(name="example", module=module,
                             data={"dir": str(tmp_path), "level": "custom"})
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    with pytest.raises(ServerError, match="Procedural Map"):
        Server.wipe(server, yes=True)


def test_necesse_wipe_supports_explicit_external_datadir(tmp_path, monkeypatch):
    module = import_module("gamemodules.necserver")
    install = tmp_path / "server"
    install.mkdir()
    data = tmp_path / "data"
    (data / "saves").mkdir(parents=True)
    (data / "saves/example.zip").write_text("world")
    (data / "saves/other.zip").write_text("other")
    server = SimpleNamespace(name="example", module=module, data={
        "dir": str(install), "datadir": str(data), "world": "example",
    })
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    Server.wipe(server, yes=True)
    assert not (data / "saves/example.zip").exists()
    assert (data / "saves/other.zip").exists()


@pytest.mark.parametrize("module_name,world", [("necserver", ""), ("necserver", "."),
                                             ("terraria.tshock", ""), ("terraria", ".")])
def test_reset_refuses_world_name_that_means_entire_save_directory(tmp_path, monkeypatch, module_name, world):
    module = import_module("gamemodules." + module_name)
    (tmp_path / "saves").mkdir()
    (tmp_path / "Worlds").mkdir()
    server = SimpleNamespace(name="example", module=module, data={
        "dir": str(tmp_path), "datadir": str(tmp_path), "world": world,
    })
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    with pytest.raises(ServerError, match="[Ww]orld"):
        Server.wipe(server, yes=True)
    assert (tmp_path / "saves").exists()
    assert (tmp_path / "Worlds").exists()


@pytest.mark.parametrize("world", ["", ".", "nested/..", "../other", "/tmp/other"])
@pytest.mark.parametrize("properties", [False, True])
def test_bedrock_reset_refuses_broad_or_escaping_world_name(tmp_path, monkeypatch, world, properties):
    module = import_module("gamemodules.minecraft.bedrock")
    (tmp_path / "worlds").mkdir()
    (tmp_path / "worlds" / "other").mkdir()
    if properties:
        (tmp_path / "server.properties").write_text("level-name=" + world + "\n")
    server = SimpleNamespace(name="example", module=module,
                             data={"dir": str(tmp_path), "levelname": world})
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    with pytest.raises(ServerError):
        Server.wipe(server, yes=True)
    assert (tmp_path / "worlds" / "other").exists()


@pytest.mark.parametrize("line", ["level-name: actual", "level-name actual", "level-name = actual"])
def test_minecraft_wipe_reads_native_property_separators(tmp_path, line):
    module = import_module("gamemodules.minecraft.vanilla")
    (tmp_path / "server.properties").write_text(line + "\n")
    server = SimpleNamespace(name="example", data={"dir": str(tmp_path)})
    assert module.get_wipe_paths(server) == ["actual"]


@pytest.mark.parametrize("line", [r"level\u002dname=actual", "level-name=actual\\\ncontinued",
                                  "level-name=actual "])
def test_minecraft_wipe_refuses_ambiguous_property_syntax(tmp_path, line):
    module = import_module("gamemodules.minecraft.vanilla")
    (tmp_path / "server.properties").write_text(line + "\n")
    server = SimpleNamespace(name="example", data={"dir": str(tmp_path)})
    with pytest.raises(ServerError):
        module.get_wipe_paths(server)


@pytest.mark.parametrize("world", ["plugins", "server.properties"])
def test_minecraft_reset_refuses_non_world_targets(tmp_path, monkeypatch, world):
    module = import_module("gamemodules.minecraft.vanilla")
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "important.jar").write_text("plugin")
    (tmp_path / "server.properties").write_text("level-name=" + world + "\n")
    server = SimpleNamespace(name="example", module=module, data={"dir": str(tmp_path)})
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    with pytest.raises(ServerError, match="world directory"):
        Server.wipe(server, yes=True)
    assert (tmp_path / "plugins" / "important.jar").exists()
    assert (tmp_path / "server.properties").exists()


def test_necesse_world_named_worlds_does_not_reset_other_worlds(tmp_path, monkeypatch):
    module = import_module("gamemodules.necserver")
    (tmp_path / "saves" / "worlds").mkdir(parents=True)
    (tmp_path / "saves" / "worlds" / "worlds.zip").write_text("selected")
    other = tmp_path / "saves" / "worlds" / "other.zip"
    other.write_text("preserve")
    server = SimpleNamespace(name="example", module=module, data={
        "dir": str(tmp_path), "datadir": str(tmp_path), "world": "worlds",
    })
    monkeypatch.setattr(runtime_module, "check_server_running", lambda server: False)
    Server.wipe(server, yes=True)
    assert not (tmp_path / "saves" / "worlds" / "worlds.zip").exists()
    assert other.read_text() == "preserve"
