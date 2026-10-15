"""ARK native Linux mod decompression, descriptors and ordered activation."""

import io
from pathlib import Path
import re
import struct
from tempfile import TemporaryDirectory
import zlib

from server import ServerError
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.owned_payloads import publish_owned_payloads
from server.modsupport.workshop_downloads import download_workshop_items

CONFIG = "ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini"
OWNER = "ark_workshop"
MAX_METADATA = 1024 * 1024
MAX_FILE = 1024 * 1024 * 1024
MAX_MOD = 8 * MAX_FILE


def _read_exact(handle, size):
    """Reject truncated native metadata and compressed streams."""
    value = handle.read(size)
    if len(value) != size:
        raise ServerError("Truncated ARK Workshop payload")
    return value


def _string(handle):
    """Read a bounded Unreal FString without trusting its size prefix."""
    offset = handle.tell()
    size = struct.unpack("<i", _read_exact(handle, 4))[0]
    # Unreal serializes an empty FString as int32(0), with no terminator bytes.
    # ARK metadata readers also accept this for optional mod names/values:
    # Bletch1971/ServerManagers, Utils/ModUtils.cs::ReadUE4String.
    if size == 0:
        return ""
    if not -32768 <= size <= 65536:
        raise ServerError(f"Invalid ARK metadata string length {size} at byte {offset}")
    raw = _read_exact(handle, size if size > 0 else -2 * size)
    encoding, terminator = ("utf-8", b"\0") if size > 0 else ("utf-16-le", b"\0\0")
    if not raw.endswith(terminator):
        raise ServerError("ARK metadata string has no terminator")
    try:
        value = raw[:-len(terminator)].decode(encoding)
    except UnicodeError as exc:
        raise ServerError("Invalid ARK metadata string encoding") from exc
    if "\0" in value:
        raise ServerError("ARK metadata string contains embedded NUL")
    return value


def _encode_string(value):
    """Serialize a native UTF-8 FString with its terminating byte."""
    raw = value.encode("utf-8") + b"\0"
    return struct.pack("<I", len(raw)) + raw


def _metadata(path):
    """Read only bounded native metadata files."""
    with path.open("rb") as handle:
        raw = handle.read(MAX_METADATA + 1)
    if len(raw) > MAX_METADATA:
        raise ServerError("ARK Workshop metadata exceeds the size limit")
    return raw


def _descriptor(item, root, *, declared_maps=None):
    """Build ARK's binary .mod descriptor from validated mod.info/modmeta.info."""
    info = io.BytesIO(_metadata(root / "mod.info"))
    name = _string(info)
    count = struct.unpack("<I", _read_exact(info, 4))[0]
    if count > 4096:
        raise ServerError("ARK Workshop metadata has too many maps")
    maps = [_string(info) for _index in range(count)]
    if len(info.read()) not in (0, 8):
        raise ServerError("Invalid trailing ARK mod.info metadata")
    raw_meta = _metadata(root / "modmeta.info")
    metadata = io.BytesIO(raw_meta)
    pair_count = struct.unpack("<I", _read_exact(metadata, 4))[0]
    if pair_count > 4096:
        raise ServerError("ARK Workshop metadata has too many properties")
    pairs = {_string(metadata): _string(metadata) for _index in range(pair_count)}
    if metadata.read() or pairs.get("ModType") not in ("1", "2"):
        raise ServerError("Only ARK gameplay mods (ModType 1) and maps (ModType 2) are supported")
    if pairs["ModType"] == "2":
        if not maps or any(not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", value) for value in maps):
            raise ServerError("ARK map metadata must declare safe native map names")
        if declared_maps is not None:
            declared_maps[item] = maps
    result = struct.pack("<Q", int(item)) + _encode_string(name)
    result += _encode_string(f"../../../ShooterGame/Content/Mods/{item}")
    result += struct.pack("<I", count) + b"".join(_encode_string(value) for value in maps)
    return result + b"\x33\xff\x22\xff\x02\0\0\0\x01" + raw_meta


def decompress_ark_file(source, destination):
    """Stream Unreal's bounded chunked zlib format, verifying all declared sizes."""
    with source.open("rb") as handle:
        magic, chunk_size, compressed_total, total = struct.unpack("<4Q", _read_exact(handle, 32))
        if (magic != 0x9E2A83C1 or not 0 < chunk_size <= 16 * 1024 * 1024
                or not 0 < total <= MAX_FILE or not 0 < compressed_total <= MAX_FILE):
            raise ServerError("Invalid ARK compressed header or size limit")
        count = (total + chunk_size - 1) // chunk_size
        if count > 65536:
            raise ServerError("ARK compressed chunk count exceeds the limit")
        chunks = [struct.unpack("<2Q", _read_exact(handle, 16)) for _index in range(count)]
        if (sum(chunk[0] for chunk in chunks) != compressed_total
                or sum(chunk[1] for chunk in chunks) != total
                or any(not 0 < packed <= 32 * 1024 * 1024 or not 0 < plain <= chunk_size
                       for packed, plain in chunks)):
            raise ServerError("Invalid ARK compressed chunk sizes")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as output:
            for packed, plain in chunks:
                decoder = zlib.decompressobj()
                try:
                    content = decoder.decompress(_read_exact(handle, packed), plain + 1)
                except zlib.error as exc:
                    raise ServerError("Invalid ARK compressed stream") from exc
                if (len(content) != plain or not decoder.eof or decoder.unused_data
                        or decoder.unconsumed_tail):
                    raise ServerError("ARK compressed stream does not match its declared size")
                output.write(content)
        if handle.read(1):
            raise ServerError("ARK compressed file has trailing data")
    size_file = source.with_name(source.name + ".uncompressed_size")
    if size_file.exists():
        raw = _metadata(size_file).strip()
        if not raw.isdigit() or int(raw) != total:
            raise ServerError("ARK uncompressed-size sidecar differs from the chunk header")
    return total


def _prepare_files(payloads, scratch, *, map_catalog=None):
    """Validate every item before publishing any native descriptor or asset."""
    files = {}
    declared_maps = {}
    for item, payload in payloads.items():
        entries = []
        for path in payload.rglob("*"):
            entries.append(path)
            if len(entries) > 10000:
                raise ServerError("ARK Workshop payload exceeds file limit")
        if len(entries) > 10000 or payload.is_symlink() or any(path.is_symlink() for path in entries):
            raise ServerError("ARK Workshop payload contains symlinks or exceeds file limit")
        root = payload / "LinuxNoEditor"
        if not root.is_dir():
            raise ServerError("ARK Workshop mod has no native LinuxNoEditor content")
        files[f"ShooterGame/Content/Mods/{item}.mod"] = _descriptor(
            item, root, declared_maps=declared_maps)
        size = 0
        for source in sorted(path for path in entries if root in path.parents):
            if not source.is_file() or source.name.endswith(".z.uncompressed_size"):
                continue
            relative = source.relative_to(root)
            target = f"ShooterGame/Content/Mods/{item}/{relative.as_posix()}"
            if source.suffix == ".z":
                relative = relative.with_suffix("")
                unpacked = scratch / item / relative
                size += decompress_ark_file(source, unpacked)
                target = f"ShooterGame/Content/Mods/{item}/{relative.as_posix()}"
                files[target] = unpacked
            else:
                size += source.stat().st_size
                files[target] = source
            if size > MAX_MOD:
                raise ServerError("ARK Workshop mod exceeds the 8 GiB unpacked limit")
        native_maps = {}
        for name in declared_maps.get(item, []):
            prefix = f"ShooterGame/Content/Mods/{item}/"
            candidates = [path for path in files if path.startswith(prefix)
                          and Path(path).name == name + ".umap"]
            if len(candidates) != 1:
                raise ServerError("ARK map metadata must resolve to one staged native .umap: " + name)
            launch = "/Game/Mods/" + item + "/" + candidates[0][len(prefix):-5]
            if not re.fullmatch(r"/Game/Mods/[0-9]+/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", launch):
                raise ServerError("ARK map payload has an unsafe native map path")
            native_maps[name] = launch
        if native_maps and map_catalog is not None:
            map_catalog[item] = native_maps
    return files


def _parse_ids(original):
    """Read the bounded, target-section native mod array without generic INI rewrites."""
    lines = (original or "").splitlines(keepends=True)
    in_section, section_end, found = False, None, []
    for index, line in enumerate(lines):
        section = re.match(r"\s*\[([^]]+)\]", line)
        if section:
            if in_section:
                section_end = index
            in_section = section.group(1).casefold() == "serversettings"
            if in_section:
                section_end = len(lines)
        if in_section:
            match = re.match(r"(\s*ActiveMods\s*=\s*)([^;\r\n]*)(.*)", line, re.IGNORECASE)
            if match:
                found.append((index, match))
    if len(found) > 1:
        raise ServerError("ARK configuration has duplicate ActiveMods entries")
    existing = found[0][1].group(2).strip().split(",") if found else []
    existing = [value.strip() for value in existing if value.strip()]
    if any(not value.isascii() or not value.isdigit() or not 0 < int(value) < 2**64 for value in existing):
        raise ServerError("ARK ActiveMods must contain positive numeric Workshop IDs")
    return lines, section_end, found, existing


def configured_workshop_ids(server):
    """Read the last prestart snapshot without opening an engine-owned live INI."""
    state = server.data.get("mods", {})
    values = state.get("ark_workshop_launch_ids", state.get("ark_workshop_ids", []))
    if (not isinstance(values, list) or any(not isinstance(value, str) or not value.isascii()
            or not value.isdigit() or not 0 < int(value) < 2**64 for value in values)):
        raise ServerError("Invalid ARK Workshop launch snapshot")
    maps = state.get("ark_workshop_maps", {})
    return [item for item in values if not isinstance(maps, dict) or item not in maps]


def configured_workshop_map(server, value=None):
    """Use validated staged map paths without reopening engine-owned live files."""
    selected = str(server.data["map"] if value is None else value)
    if not selected.startswith("/Game/Mods/"):
        return selected
    state = server.data.get("mods", {})
    maps = state.get("ark_workshop_maps", {})
    if isinstance(maps, dict):
        for item, entries in maps.items():
            if isinstance(item, str) and isinstance(entries, dict) and selected in entries.values():
                if re.fullmatch(r"/Game/Mods/" + re.escape(item)
                                + r"/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+", selected):
                    return selected
    raise ServerError("Custom ARK map must belong to a staged, active Workshop map")


def refresh_launch_workshop_ids(server):
    """Snapshot merged operator and managed IDs while the engine is stopped."""
    config = safe_server_path(server, CONFIG)
    original = _metadata(config).decode("utf-8-sig") if config.exists() else None
    server.data.setdefault("mods", {})["ark_workshop_launch_ids"] = _parse_ids(original)[3]
    server.data.save()


def _merge_ids(original, previous, desired):
    """Change only ActiveMods, retaining all unrelated INI lines and comments."""
    lines, section_end, found, existing = _parse_ids(original)
    operator = [value for value in existing if value not in previous]
    owned = [value for value in desired if value not in operator]
    value = ",".join(dict.fromkeys(operator + owned))
    if found:
        index, match = found[0]
        lines[index] = match.group(1) + value + match.group(3) + "\n"
    elif section_end is not None:
        if section_end and not lines[section_end - 1].endswith("\n"):
            lines[section_end - 1] += "\n"
        lines.insert(section_end, "ActiveMods=" + value + "\n")
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.extend(["[ServerSettings]\n", "ActiveMods=" + value + "\n"])
    return "".join(lines), owned


def configure_workshop(server, item_ids):
    """Reconcile ordered native activation and payload ownership transactionally."""
    state = server.data.setdefault("mods", {})
    previous = state.get("ark_workshop_ids", [])
    if not isinstance(previous, list) or any(not isinstance(value, str) for value in previous):
        raise ServerError("Invalid ARK Workshop ownership state")
    if not item_ids and not previous and not state.get("ark_workshop_maps"):
        return []
    config = safe_server_path(server, CONFIG)
    original = _metadata(config).decode("utf-8-sig") if config.exists() else None
    payloads = download_workshop_items(server, 346110, item_ids) if item_ids else {}
    scratch = safe_server_path(server, ".alphagsm/ark-unpacked")
    scratch.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=scratch) as directory:
        maps = {}
        files = _prepare_files(payloads, Path(directory), map_catalog=maps)
        text, owned = _merge_ids(original, previous, [item for item in item_ids if item not in maps])
        if len(text.encode("utf-8")) > MAX_METADATA:
            raise ServerError("ARK configuration exceeds size limit")
        write_managed_text(server, CONFIG, text)
        had_ids = "ark_workshop_ids" in state
        had_launch_ids = "ark_workshop_launch_ids" in state
        previous_launch_ids = state.get("ark_workshop_launch_ids")
        previous_maps = state.get("ark_workshop_maps")
        state["ark_workshop_ids"] = owned
        state["ark_workshop_launch_ids"] = _parse_ids(text)[3]
        state["ark_workshop_maps"] = maps
        try:
            paths = publish_owned_payloads(server, OWNER, files)
        except BaseException:
            if had_ids:
                state["ark_workshop_ids"] = previous
            else:
                state.pop("ark_workshop_ids", None)
            if had_launch_ids:
                state["ark_workshop_launch_ids"] = previous_launch_ids
            else:
                state.pop("ark_workshop_launch_ids", None)
            if previous_maps is None:
                state.pop("ark_workshop_maps", None)
            else:
                state["ark_workshop_maps"] = previous_maps
            if original is None:
                safe_server_path(server, CONFIG).unlink(missing_ok=True)
            else:
                write_managed_text(server, CONFIG, original)
            raise
    return [CONFIG, *paths]
