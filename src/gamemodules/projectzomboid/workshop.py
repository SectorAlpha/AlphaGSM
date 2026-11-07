"""Discover build-compatible native Project Zomboid Workshop activation IDs."""

import os
from pathlib import Path
import re
from struct import unpack_from, error as StructError
from zipfile import BadZipFile, ZipFile

from server.errors import ServerError
from server.modsupport.workshop import validate_workshop_identifier

WORKSHOP_APP_ID = 108600
_METADATA_LIMIT = 128 * 1024
MAX_CONFIG_BYTES = 1024 * 1024


def download_workshop_items(server, app_id, item_ids):
    """Use the shared validated download cache without copying native game files."""
    from server.modsupport.workshop_downloads import download_workshop_items as download
    return download(server, app_id, item_ids)


def _safe_tree(root):
    """Reject symlink metadata and payload trees before reading mod identities."""
    if root.absolute() != root.resolve():
        raise ServerError("Refusing symlinked Project Zomboid Workshop payload")
    for index, (directory, subdirs, filenames) in enumerate(os.walk(root, followlinks=False)):
        if index >= 4096:
            raise ServerError("Project Zomboid Workshop payload exceeds directory limit")
        if any((Path(directory) / name).is_symlink() for name in subdirs + filenames):
            raise ServerError("Refusing symlinked Project Zomboid Workshop metadata")


def _version(value):
    if not re.fullmatch(r"\d+\.\d+(?:\.\d+)?", value):
        raise ServerError(f"Invalid Project Zomboid version metadata: {value!r}")
    parts = tuple(int(part) for part in value.split("."))
    return parts + (0,) * (3 - len(parts))


def installed_game_version(server):
    """Read the installed engine's version constant, rather than assuming a branch."""
    from server.modsupport.native_workshop import safe_server_path
    core = safe_server_path(server, "zombie/core/Core.class")
    if core.is_file():
        with core.open("rb") as handle:
            raw = handle.read(1024 * 1024 + 1)
    else:
        jar = safe_server_path(server, "java/projectzomboid.jar")
        if not jar.is_file():
            raise ServerError("Cannot verify installed Project Zomboid build (engine files missing)")
        try:
            with ZipFile(jar) as archive:
                if archive.getinfo("zombie/core/Core.class").file_size > 1024 * 1024:
                    raise ServerError("Project Zomboid engine metadata exceeds size limit")
                raw = archive.read("zombie/core/Core.class")
        except (BadZipFile, KeyError) as exc:
            raise ServerError("Cannot read installed Project Zomboid engine metadata") from exc
    if len(raw) > 1024 * 1024 or not raw.startswith(b"\xca\xfe\xba\xbe"):
        raise ServerError("Cannot verify installed Project Zomboid engine version")
    # The field-linked B42 constructor wins over legacy version literals used
    # elsewhere in the class, such as old-save compatibility checks.
    try:
        versions = _constructed_game_versions(raw)
    except ServerError:
        versions = set()
    if not versions:
        # B41 stores its version as a Java UTF8 constant with a byte length.
        for match in re.finditer(rb"\x01\x00(.)(4[12]\.\d+(?:\.\d+)?)(?![\d.])", raw):
            if match.group(1)[0] == len(match.group(2)):
                versions.add(_version(match.group(2).decode("ascii")))
    if len(versions) != 1:
        raise ServerError("Cannot unambiguously verify installed Project Zomboid build")
    return versions.pop()


def _class_constants(raw):
    """Read constant-pool references without executing the installed game."""
    constants, index, cursor = {}, 1, 10
    count = unpack_from(">H", raw, 8)[0]
    while index < count:
        tag = raw[cursor]
        cursor += 1
        if tag == 1:
            size = unpack_from(">H", raw, cursor)[0]
            cursor += 2
            value = raw[cursor:cursor + size].decode("utf-8", errors="replace")
            cursor += size
        elif tag in (3, 4):
            value = unpack_from(">I", raw, cursor)[0]
            cursor += 4
        elif tag in (5, 6):
            value = raw[cursor:cursor + 8]
            cursor += 8
        elif tag in (7, 8, 16, 19, 20):
            value = unpack_from(">H", raw, cursor)[0]
            cursor += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            value = unpack_from(">HH", raw, cursor)
            cursor += 4
        elif tag == 15:
            value = raw[cursor:cursor + 3]
            cursor += 3
        else:
            raise ValueError("Unknown Java constant-pool tag")
        constants[index] = (tag, value)
        index += 2 if tag in (5, 6) else 1
    return constants


def _constructed_game_versions(raw):
    """Resolve B42's GameVersion constructor assigned to Core.gameVersion."""
    try:
        constants = _class_constants(raw)
        classes = [index for index, (tag, value) in constants.items()
                   if tag == 7 and constants[value][1] == "zombie/core/GameVersion"]
        constructors, fields = [], []
        for index, (tag, value) in constants.items():
            if tag not in (9, 10):
                continue
            class_ref, name_ref = value
            name_index, descriptor_index = constants[name_ref][1]
            name, descriptor = constants[name_index][1], constants[descriptor_index][1]
            if (tag == 10 and class_ref in classes and name == "<init>"
                    and descriptor == "(IILjava/lang/String;)V"):
                constructors.append(index)
            if tag == 9 and name == "gameVersion" and descriptor == "Lzombie/core/GameVersion;":
                fields.append(index)
        versions = set()
        for class_index in classes:
            for constructor in constructors:
                for field in fields:
                    prefix = re.escape(b"\xbb" + class_index.to_bytes(2, "big") + b"\x59")
                    suffix = re.escape(b"\xb7" + constructor.to_bytes(2, "big")
                                       + b"\xb3" + field.to_bytes(2, "big"))
                    pattern = prefix + rb"(\x10.)([\x03-\x08]|\x10.)(\x12.|\x13..)" + suffix
                    for match in re.finditer(pattern, raw, re.DOTALL):
                        major = match.group(1)[1]
                        minor_push = match.group(2)
                        minor = minor_push[0] - 3 if len(minor_push) == 1 else minor_push[1]
                        string_index = int.from_bytes(match.group(3)[1:], "big")
                        patch_text = constants[constants[string_index][1]][1]
                        if major in (41, 42) and (not patch_text or str(patch_text).isdigit()):
                            versions.add((major, minor, int(patch_text or 0)))
        return versions
    except (IndexError, KeyError, StructError, TypeError, ValueError) as exc:
        raise ServerError("Cannot parse installed Project Zomboid engine version") from exc


def _mod_id(value, item_id, *, dependency=False):
    value = value.lstrip("\\")
    if "/" in value:
        prefix, value_tail = value.split("/", 1)
        if not re.fullmatch(r"[0-9]+", prefix) or (not dependency and prefix != item_id):
            raise ServerError("Invalid Project Zomboid mod id Workshop prefix")
    else:
        value_tail = value
    if (not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_. +()@-]*", value_tail)
            or ".." in value_tail):
        raise ServerError(f"Invalid Project Zomboid mod id: {value!r}")
    return value


def _read_metadata(path, item_id, version):
    with path.open(encoding="utf-8-sig") as handle:
        raw = handle.read(_METADATA_LIMIT + 1)
    if len(raw) > _METADATA_LIMIT:
        raise ServerError("Project Zomboid mod.info exceeds size limit")
    fields = {}
    for line in raw.splitlines():
        key, separator, value = line.partition("=")
        if separator and not line.lstrip().startswith("#"):
            key, value = key.strip(), value.strip()
            if key in fields and key in ("id", "require", "versionMin", "versionMax"):
                raise ServerError(f"Duplicate Project Zomboid mod.info {key} field")
            fields[key] = value
    mod_id = _mod_id(fields.get("id", ""), item_id)
    for key, comparison in (("versionMin", lambda target: version < target),
                            ("versionMax", lambda target: version > target)):
        if fields.get(key) and comparison(_version(fields[key])):
            raise ServerError(f"Project Zomboid mod {mod_id} is not compatible with installed build")
    metadata = {key: [_mod_id(value.strip(), item_id, dependency=True)
                      for value in fields.get(key, "").split(",") if value.strip()]
                for key in ("require", "incompatible", "loadModAfter", "loadModBefore")}
    return mod_id, metadata


def _compatible_info(mod_root, version):
    if version[0] == 41:
        candidate = mod_root / "mod.info"
        return candidate if candidate.is_file() else None
    candidates = []
    for child in mod_root.iterdir():
        if child.is_dir() and re.fullmatch(r"42(?:\.\d+){0,2}", child.name):
            folder_version = tuple(int(part) for part in child.name.split("."))
            # The native B42 loader compares major/minor and ignores patch.
            score = (folder_version + (0, 0))[:2]
            if score <= version[:2]:
                candidates.append((score, child))
    if candidates:
        score = max(candidate[0] for candidate in candidates)
        winners = [child for candidate_score, child in candidates if candidate_score == score]
        if len(winners) != 1:
            raise ServerError("Ambiguous Project Zomboid version-specific mod folders")
        candidate = winners[0] / "mod.info"
        if candidate.is_file():
            return candidate
    common = mod_root / "common" / "mod.info"
    return common if common.is_file() else None


def inspect_workshop_mods(payloads, version):
    """Discover exact IDs, reject unsupported maps, and topologically order mods."""
    mods = {}
    for item_id, payload in payloads.items():
        validate_workshop_identifier(item_id)
        payload = Path(payload)
        _safe_tree(payload)
        mod_directory = payload / "mods"
        if not mod_directory.is_dir():
            raise ServerError(f"Workshop item {item_id} contains no compatible Project Zomboid mods")
        found = False
        for mod_root in sorted(mod_directory.iterdir()):
            if not mod_root.is_dir():
                continue
            info = _compatible_info(mod_root, version)
            if info is None:
                raise ServerError(f"Workshop item {item_id} has a mod incompatible with installed build")
            if any((base / "media" / "maps").exists()
                   for base in (mod_root, mod_root / "common", info.parent)):
                raise ServerError("Workshop map mods require explicit map ordering; native mod apply does not support maps")
            mod_id, metadata = _read_metadata(info, item_id, version)
            if mod_id in mods:
                raise ServerError(f"Duplicate Project Zomboid mod id: {mod_id}")
            mods[mod_id] = metadata
            found = True
        if not found:
            raise ServerError(f"Workshop item {item_id} contains no compatible Project Zomboid mods")
    return _ordered_mods(mods, version)


def _ordered_mods(mods, version):
    dependencies = {mod_id: set() for mod_id in mods}
    for mod_id, metadata in mods.items():
        for required in metadata["require"]:
            if required not in mods:
                raise ServerError(f"Missing Project Zomboid mod dependency {required} required by {mod_id}")
            dependencies[mod_id].add(required)
        for incompatible in metadata["incompatible"]:
            if incompatible in mods:
                raise ServerError(f"Incompatible Project Zomboid mods: {mod_id} and {incompatible}")
        dependencies[mod_id].update(other for other in metadata["loadModAfter"] if other in mods)
        for other in metadata["loadModBefore"]:
            if other in mods:
                dependencies[other].add(mod_id)
    ordered = []
    while len(ordered) < len(mods):
        ready = [mod_id for mod_id in mods if mod_id not in ordered
                 and dependencies[mod_id].issubset(ordered)]
        if not ready:
            raise ServerError("Cyclic Project Zomboid mod dependency or load order")
        ordered.extend(ready)
    return [("\\" if version[0] >= 42 else "") + mod_id for mod_id in ordered]


def validate_servername(server, value):
    """Reject profile escapes and keep activation ownership tied to its profile."""
    name = str(value)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise ServerError("Project Zomboid servername must contain only letters, digits, _ or -")
    previous = server.data.get("projectzomboid_workshop", {})
    if (name != server.data.get("servername", name)
            and (previous.get("Mods") or previous.get("WorkshopItems"))):
        raise ServerError("Clean up native Workshop activation before changing servername")
    return name


def config_relative_path(server):
    """Keep native profiles inside the install mount for process/Docker parity."""
    name = validate_servername(server, server.data.get("servername", server.name))
    return f"Zomboid/Server/{name}.ini"


def _read_config(server):
    from server.modsupport.native_workshop import safe_server_path
    relative = config_relative_path(server)
    path = safe_server_path(server, relative)
    if not path.exists():
        legacy = Path.home() / "Zomboid" / "Server" / path.name
        if legacy.is_file():
            raise ServerError("Existing home-directory Project Zomboid profile found; move its profile and save data into the install Zomboid directory before using native Workshop activation")
        return relative, []
    with path.open("rb") as handle:
        raw = handle.read(MAX_CONFIG_BYTES + 1)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ServerError("Project Zomboid server INI exceeds size limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise ServerError("Project Zomboid server INI has invalid UTF-8 encoding") from exc
    return relative, text.splitlines(keepends=True)


def _replace_keys(lines, replacements):
    seen = set()
    updated = []
    for line in lines:
        key, separator, _ = line.partition("=")
        key = key.strip()
        if separator and key in replacements:
            if key in seen:
                raise ServerError(f"Duplicate Project Zomboid INI key: {key}")
            seen.add(key)
            updated.append(f"{key}={replacements[key]}\n")
        else:
            updated.append(line)
    for key, value in replacements.items():
        if key not in seen:
            if updated and not updated[-1].endswith("\n"):
                updated[-1] += "\n"
            updated.append(f"{key}={value}\n")
    text = "".join(updated)
    if len(text.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise ServerError("Project Zomboid server INI exceeds size limit")
    return text


def sync_server_config(server):
    """Preserve native settings while synchronizing explicitly managed ports."""
    from server.modsupport.native_workshop import write_managed_text
    relative, lines = _read_config(server)
    replacements = {"DefaultPort": str(int(server.data["port"])),
                    "UDPPort": str(int(server.data.get("queryport", 16262)))}
    write_managed_text(server, relative, _replace_keys(lines, replacements))


def apply_workshop_mods(server, item_ids):
    """Validate downloaded identities before editing native WorkshopItems/Mods."""
    from server.modsupport.native_workshop import write_managed_text
    identifiers = [validate_workshop_identifier(item) for item in item_ids]
    if len(set(identifiers)) != len(identifiers):
        raise ServerError("Duplicate Project Zomboid Workshop item id")
    relative, lines = _read_config(server)
    previous = server.data.get("projectzomboid_workshop", {})
    if previous.get("profile", relative) != relative and previous.get("Mods"):
        raise ServerError("Clean up native Workshop activation before changing servername")
    mod_ids = (inspect_workshop_mods(download_workshop_items(server, WORKSHOP_APP_ID, identifiers),
                                     installed_game_version(server)) if identifiers else [])
    replacements, ownership = {}, {"profile": relative}
    for key, desired in (("WorkshopItems", identifiers), ("Mods", mod_ids)):
        values = []
        for line in lines:
            name, separator, value = line.partition("=")
            if separator and name.strip() == key:
                values.extend(part.strip() for part in value.strip().split(";") if part.strip())
        operator = [value for value in values if value not in previous.get(key, [])]
        added = [value for value in desired if value not in operator]
        replacements[key] = ";".join(operator + added)
        ownership[key] = added
    write_managed_text(server, relative, _replace_keys(lines, replacements))
    server.data["projectzomboid_workshop"] = ownership
    server.data.save()
    return [relative]
