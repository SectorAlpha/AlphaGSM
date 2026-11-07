"""Inspect real TMOD packages and configure the native server mod loader."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct

from server.errors import ServerError
from server.modsupport import owned_payloads
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.workshop_downloads import download_workshop_items


def _read(handle, size):
    value = handle.read(size)
    if len(value) != size:
        raise ServerError('Truncated TMOD package')
    return value


def _string(handle):
    length = 0
    for index in range(5):
        byte = _read(handle, 1)[0]
        length |= (byte & 127) << (index * 7)
        if not byte & 128:
            break
    else:
        raise ServerError('Invalid TMOD string length')
    if not 0 < length <= 4096:
        raise ServerError('TMOD string exceeds the metadata limit')
    return _read(handle, length).decode('utf-8')


def _version(value):
    value = str(value).removeprefix('v')
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,3}', value):
        raise ServerError('Invalid tModLoader package or release version')
    parts = tuple(int(part) for part in value.split('.'))
    return parts + (0,) * (4 - len(parts))


def _read_table(handle, size):
    count = struct.unpack('<i', _read(handle, 4))[0]
    if not 0 <= count <= 100000:
        raise ServerError('Invalid TMOD file count')
    names = set()
    total = 0
    for _ in range(count):
        name = _string(handle)
        path = PurePosixPath(name)
        if ('\\' in name or path.is_absolute() or any(part in ('', '.', '..') for part in name.split('/'))
                or name.casefold() in names):
            raise ServerError('Unsafe or duplicate TMOD internal path')
        names.add(name.casefold())
        unpacked, stored = struct.unpack('<ii', _read(handle, 8))
        if unpacked < 0 or stored < 0 or stored > unpacked:
            raise ServerError('Invalid TMOD file size')
        total += stored
    if total != size - handle.tell():
        raise ServerError('TMOD file table does not match the payload size')


def inspect_tmod(path):
    """Validate TMOD identity, data hash and file table using the upstream format."""
    try:
        size = path.stat().st_size
        with path.open('rb') as handle:
            if _read(handle, 4) != b'TMOD':
                raise ServerError('Invalid TMOD package header')
            version = _version(_string(handle))
            expected = _read(handle, 20)
            _read(handle, 256)
            length = struct.unpack('<i', _read(handle, 4))[0]
            start = handle.tell()
            if length != size - start:
                raise ServerError('Invalid TMOD payload length')
            digest = hashlib.sha1()
            for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                digest.update(chunk)
            if digest.digest() != expected:
                raise ServerError('TMOD payload hash mismatch')
            handle.seek(start)
            name = _string(handle)
            _version(_string(handle))
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,100}', name):
                raise ServerError('Unsafe TMOD internal mod name')
            _read_table(handle, size)
            return name, version
    except (UnicodeError, OSError, struct.error) as exc:
        raise ServerError(f'Cannot inspect TMOD package: {exc}') from exc


def select_workshop_packages(downloads, release):
    """Select each item's latest compatible 1.4.4 mod package without guessing IDs."""
    selected = {}
    current = _version(release)
    for item, root in downloads.items():
        candidates = []
        for directory, subdirectories, filenames in os.walk(root, followlinks=False):
            if any((Path(directory) / name).is_symlink() for name in subdirectories + filenames):
                raise ServerError('Refusing symlinked tModLoader Workshop payload')
            for filename in filenames:
                if filename.lower().endswith('.tmod'):
                    path = Path(directory) / filename
                    name, version = inspect_tmod(path)
                    if (2023, 6, 0, 0) <= version <= current:
                        candidates.append((version, name, path))
        if not candidates:
            raise ServerError(f'Workshop item {item} has no compatible tModLoader 1.4.4 package')
        candidates.sort(key=lambda record: record[0], reverse=True)
        version, name, path = candidates[0]
        if any(other_name != name or other_version == version
               for other_version, other_name, _path in candidates[1:]):
            raise ServerError(f'Workshop item {item} has ambiguous TMOD packages')
        if name.casefold() in {old.casefold() for old in selected}:
            raise ServerError(f'Duplicate internal TMOD mod name: {name}')
        selected[name] = path
    return selected


def apply_workshop_mods(server, item_ids):
    """Publish owned packages and preserve unrelated native enabled-mod entries."""
    downloads = download_workshop_items(server, 1281930, item_ids) if item_ids else {}
    packages = select_workshop_packages(downloads, server.data['version'])
    enabled = safe_server_path(server, 'Mods/enabled.json')
    original = enabled.read_text(encoding='utf-8') if enabled.exists() else None
    try:
        existing = json.loads(original) if original is not None else []
    except ValueError as exc:
        raise ServerError('Native Mods/enabled.json must contain a JSON name list') from exc
    if not isinstance(existing, list) or any(not isinstance(name, str) for name in existing):
        raise ServerError('Native Mods/enabled.json must contain a JSON name list')
    mods = server.data.setdefault('mods', {})
    had_names = 'tmodloader_owned_names' in mods
    previous = mods.get('tmodloader_owned_names', [])
    retained = [name for name in existing if name not in previous]
    additions = [name for name in packages if name not in retained]
    files = {'Mods/' + name + '.tmod': path for name, path in packages.items()}
    write_managed_text(server, 'Mods/enabled.json', json.dumps(retained + additions, indent=2) + '\n')
    mods['tmodloader_owned_names'] = additions
    try:
        owned_payloads.publish_owned_payloads(server, 'tmodloader', files)
    except BaseException:
        if had_names:
            mods['tmodloader_owned_names'] = previous
        else:
            mods.pop('tmodloader_owned_names', None)
        if original is None:
            safe_server_path(server, 'Mods/enabled.json').unlink()
        else:
            write_managed_text(server, 'Mods/enabled.json', original)
        raise
    return ['Mods/enabled.json']
