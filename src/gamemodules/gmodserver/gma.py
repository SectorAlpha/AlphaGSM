"""Bounded, validated extraction of Facepunch's version-3 GMAD addon format.

Format: https://github.com/Facepunch/gmad/blob/master/src/create_gmad.cpp
"""

from pathlib import Path, PurePosixPath
import struct
import zlib

from server.modsupport.errors import ModSupportError

MAX_GMA_BYTES = 2 * 1024 ** 3
MAX_GMA_FILES = 10000


def _read(handle, size):
    data = handle.read(size)
    if len(data) != size:
        raise ModSupportError("Truncated GMA addon")
    return data


def _string(handle, limit=1024):
    data = bytearray()
    while len(data) <= limit:
        character = _read(handle, 1)
        if character == b"\0":
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ModSupportError("Invalid GMA string encoding") from exc
        data.extend(character)
    raise ModSupportError("GMA string exceeds size limit")


def _crc(handle, size):
    result = 0
    while size:
        block = _read(handle, min(size, 1024 * 1024))
        result = zlib.crc32(block, result)
        size -= len(block)
    return result


def _entries(handle, archive_size):
    if _read(handle, 5) != b"GMAD\x03":
        raise ModSupportError("Invalid GMA signature or version")
    _read(handle, 16)  # Steam ID and timestamp.
    for _ in range(128):
        if not _string(handle):
            break
    else:
        raise ModSupportError("GMA required-content list exceeds limit")
    for _ in range(3):
        _string(handle, 1024 * 1024)  # Name, description and author.
    _read(handle, 4)  # Addon version.
    entries, names = [], set()
    while True:
        index = struct.unpack("<I", _read(handle, 4))[0]
        if not index:
            break
        if index != len(entries) + 1 or len(entries) >= MAX_GMA_FILES:
            raise ModSupportError("Invalid GMA file index or file count")
        name = _string(handle)
        path = PurePosixPath(name)
        if (path.is_absolute() or any(part in ("", ".", "..") for part in name.split("/"))
                or any(char in name for char in "\\:*?<>|\"")
                or any(ord(char) < 32 for char in name) or name.casefold() in names):
            raise ModSupportError("Unsafe or duplicate GMA file path")
        names.add(name.casefold())
        size, checksum = struct.unpack("<qI", _read(handle, 12))
        if not 0 < size <= MAX_GMA_BYTES:
            raise ModSupportError("Invalid GMA file size")
        entries.append((path, size, checksum))
    if not entries or handle.tell() + sum(size for _, size, _ in entries) + 4 != archive_size:
        raise ModSupportError("GMA payload size does not match its file table")
    if any(str(parent).casefold() in names for path, _, _ in entries for parent in path.parents):
        raise ModSupportError("Conflicting GMA file and directory paths")
    return entries


def extract_gma(archive, destination):
    """Validate the complete file table and CRCs before creating any addon files."""
    archive, destination = Path(archive), Path(destination)
    if archive.is_symlink() or not archive.is_file():
        raise ModSupportError("GMA addon must be a regular file")
    size = archive.stat().st_size
    if not 30 <= size <= MAX_GMA_BYTES:
        raise ModSupportError("Invalid GMA archive size")
    if destination.exists() or any(path.is_symlink() for path in (destination, *destination.parents)):
        raise ModSupportError("Refusing GMA extraction into existing or symlink paths")
    with archive.open("rb") as handle:
        archive_crc = _crc(handle, size - 4)
        expected_crc = struct.unpack("<I", _read(handle, 4))[0]
        # Upstream gmad's documented -nocrc mode records zero checksums.
        if expected_crc and archive_crc != expected_crc:
            raise ModSupportError("GMA archive CRC mismatch")
        handle.seek(0)
        entries = _entries(handle, size)
        payload_offset = handle.tell()
        for _, file_size, checksum in entries:
            actual_crc = _crc(handle, file_size)
            if checksum and actual_crc != checksum:
                raise ModSupportError("GMA file CRC mismatch")
        handle.seek(payload_offset)
        for path, file_size, _ in entries:
            output = destination / path
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as target:
                while file_size:
                    block = _read(handle, min(file_size, 1024 * 1024))
                    target.write(block)
                    file_size -= len(block)
