"""Configure anonymous Workshop packages through Avorion's native loader."""

import os
from pathlib import Path
import re

from server.errors import ServerError
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.workshop_downloads import download_workshop_items
from .lua_metadata import parse_metadata

WORKSHOP_APP_ID = 445220
BEGIN = "-- BEGIN AlphaGSM Workshop\n"
END = "-- END AlphaGSM Workshop\n"


def _config_path(server):
    galaxy = str(server.data.get("galaxy", server.name))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 _-]{0,127}", galaxy):
        raise ServerError("Avorion Workshop galaxy must be a contained directory name")
    return f"galaxies/{galaxy}/modconfig.lua"


def _metadata(server, item, source):
    root = Path(server.data["dir"]).resolve()
    try:
        relative = source.absolute().relative_to(root)
    except ValueError as exc:
        raise ServerError("Avorion Workshop payload is outside server root") from exc
    safe_server_path(server, relative)
    for index, (directory, subdirs, files) in enumerate(os.walk(source, followlinks=False)):
        if index >= 4096:
            raise ServerError("Avorion Workshop payload exceeds directory limit")
        if any((Path(directory) / name).is_symlink() for name in subdirs + files):
            raise ServerError("Refusing symlinked Avorion Workshop payload")
    path = safe_server_path(server, relative / "modinfo.lua")
    if not path.is_file() or path.stat().st_size > 128 * 1024:
        raise ServerError("Avorion Workshop item needs bounded root modinfo.lua")
    metadata = parse_metadata(path.read_text(encoding="utf-8-sig"))
    if metadata.get("id") != item or not metadata.get("name") or metadata.get("type") != "mod":
        raise ServerError("Avorion Workshop item has invalid native identity or type")
    if metadata.get("clientSideOnly") is True:
        raise ServerError("Client-only Avorion content is not dedicated server content")
    dependencies = metadata.get("dependencies", [])
    if not isinstance(dependencies, list) or any(not isinstance(dep, dict) or not isinstance(dep.get("id"), str) for dep in dependencies):
        raise ServerError("Invalid Avorion dependency metadata")
    return metadata


def _order(metadata):
    ordered, active = [], set()
    def visit(item):
        if item in ordered:
            return
        if item in active:
            raise ServerError("Avorion dependency cycle")
        active.add(item)
        for dependency in metadata[item].get("dependencies", []):
            required = dependency["id"]
            if required == "Avorion":
                continue  # The native engine checks game version ranges.
            if required in metadata:
                if dependency.get("incompatible"):
                    raise ServerError("Incompatible Avorion dependency is configured")
                if not _compatible_version(metadata[required].get("version", ""), dependency):
                    raise ServerError(f"Avorion dependency {required} has an incompatible version")
                visit(required)
            elif not dependency.get("optional") and not dependency.get("incompatible"):
                raise ServerError(f"Add required Avorion dependency {required} to desired Workshop items")
        active.remove(item)
        ordered.append(item)
    for item in metadata:
        visit(item)
    return ordered


def _version(value, upper=False):
    if not isinstance(value, str) or not re.fullmatch(r"(?:\d+|\*)(?:\.(?:\d+|\*)){0,2}", value):
        raise ServerError("Invalid Avorion dependency version")
    parts = [int(part) if part != "*" else (2**31 if upper else 0) for part in value.split(".")]
    return tuple(parts + [(2**31 if upper else 0)] * (3 - len(parts)))


def _compatible_version(actual, dependency):
    actual = _version(actual)
    minimum = dependency.get("exact", dependency.get("min"))
    maximum = dependency.get("exact", dependency.get("max"))
    return ((minimum is None or actual >= _version(minimum))
            and (maximum is None or actual <= _version(maximum, upper=True)))


def _read_config(server, relative):
    path = safe_server_path(server, relative)
    if path.exists() and path.stat().st_size > 1024 * 1024:
        raise ServerError("Avorion modconfig.lua exceeds size limit")
    return path.read_text(encoding="utf-8") if path.exists() else None


def _remove_block(original, previous):
    text = original or ""
    if previous:
        if text.count(previous) != 1:
            raise ServerError("Managed Avorion Workshop block changed externally; preserving it")
        return text.replace(previous, "", 1)
    if BEGIN in text or END in text:
        raise ServerError("Unowned Avorion Workshop block already exists")
    return text


def _publish_configs(server, originals, changes, state):
    prior = server.data.get("avorion_workshop")
    published = []
    try:
        for relative, text in changes.items():
            write_managed_text(server, relative, text)
            published.append(relative)
        server.data["avorion_workshop"] = state
        server.data.save()
    except BaseException:
        if prior is None:
            server.data.pop("avorion_workshop", None)
        else:
            server.data["avorion_workshop"] = prior
        for relative in reversed(published):
            original = originals[relative]
            if original is None:
                safe_server_path(server, relative).unlink(missing_ok=True)
            else:
                write_managed_text(server, relative, original)
        raise


def apply_workshop(server, item_ids):
    """Append a managed native Workshop block, retaining operator Lua byte for byte."""
    relative = _config_path(server)
    prior = server.data.get("avorion_workshop", {})
    previous = prior.get("block", "")
    if not item_ids and not previous:
        return []
    previous_path = prior.get("path", relative)
    originals = {previous_path: _read_config(server, previous_path)}
    changes = {previous_path: _remove_block(originals[previous_path], previous)}
    if relative != previous_path and item_ids:
        originals[relative] = _read_config(server, relative)
        changes[relative] = _remove_block(originals[relative], "")
    operator = changes.get(relative, "")
    downloaded = download_workshop_items(server, WORKSHOP_APP_ID, item_ids) if item_ids else {}
    metadata = {item: _metadata(server, item, downloaded[item]) for item in item_ids}
    ordered = _order(metadata)
    block = ""
    if ordered:
        block = ("\n" if operator and not operator.endswith("\n") else "") + BEGIN
        block += "mods = mods or {}\n"
        for item in ordered:
            block += f'table.insert(mods, {{workshopid = "{item}"}})\n'
        block += END
    if ordered:
        changes[relative] = operator + block
    _publish_configs(server, originals, changes,
                     {"block": block, "path": relative, "workshop_ids": ordered})
    return list(changes)
