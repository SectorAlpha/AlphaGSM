"""Resolve the configured Minecraft world without modifying server properties."""

from pathlib import Path
import re

from server.errors import ServerError


def _properties_world(properties, default):
    """Read ordinary property syntax and refuse forms requiring escape decoding."""

    world = default
    for line in properties.read_text(encoding="utf-8").splitlines():
        line = line.lstrip()
        if not line or line.startswith(("#", "!")):
            continue
        match = re.fullmatch(r"([^:=\s]+)(?:\s*[:=]\s*|\s+)?(.*)", line)
        if match is None:
            raise ServerError("Cannot safely parse server.properties for wipe")
        key, value = match.groups()
        if "\\" in key or line.endswith("\\"):
            raise ServerError("Escaped or continued properties require manual world reset")
        if key == "level-name":
            if value != value.strip():
                raise ServerError("Ambiguous whitespace in level-name; reset the world manually")
            world = value
    return world


def configured_world_name(server, *, default="world"):
    """Prefer the on-disk level-name actually used by the server."""

    properties = Path(server.data["dir"]) / "server.properties"
    world = str(server.data.get("levelname", default))
    if properties.is_file():
        world = _properties_world(properties, default)
    path = Path(world)
    if not world or "\\" in world or not path.parts or path.is_absolute() or ".." in path.parts:
        raise ServerError("Cannot safely resolve level-name in server.properties for wipe")
    return world


def java_world_paths(server, *, separate_dimensions=False):
    """Return the Java world directories, including Paper's split dimensions."""

    world = configured_world_name(server)
    paths = [world]
    if separate_dimensions:
        paths.extend([world + "_nether", world + "_the_end"])
    validate_world_directories(server, paths)
    return paths


def validate_world_directories(server, paths):
    """Refuse existing targets that do not have Minecraft world metadata."""

    for relative in paths:
        target = Path(server.data["dir"]) / relative
        if target.exists() and (
            not target.is_dir()
            or not any((target / marker).exists()
                       for marker in ("level.dat", "level.dat_old", "DIM-1", "DIM1"))
        ):
            raise ServerError("Not a recognized Minecraft world directory: " + str(target))
