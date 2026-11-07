"""Validated dedicated Source map assets with transactional file ownership."""

import os
from pathlib import Path
import re
import struct

from server import ServerError
from server.modsupport.native_workshop import safe_server_path
from server.modsupport.owned_payloads import publish_owned_payloads
from server.modsupport.workshop_downloads import download_workshop_items

WORKSHOP_APP_ID = 224260
GAME_DIR = 'nmrih'
OWNER = 'nmrihserver_workshop_maps'
MAP_NAME = re.compile(r'(?:nmo_|nms_)[a-zA-Z0-9_-]+\.bsp')
ASSETS = {'maps': {'.bsp', '.nav', '.ain', '.txt', '.res', '.nmo', '.nms'},
          'materials': {'.vmt', '.vtf', '.raw'}, 'models': {'.mdl', '.vtx', '.vvd', '.phy'},
          'sound': {'.wav', '.mp3', '.ogg'}, 'scripts': {'.txt'},
          'resource': {'.txt', '.res'}, 'data': {'.txt'}}


def _map_header(path):
    """Inspect bounded native BSP metadata and lump extents before publication."""
    size = path.stat().st_size
    with path.open('rb') as handle:
        header = handle.read(1036)
    if len(header) != 1036 or struct.unpack('<4si', header[:8]) not in ((b'VBSP', 20), (b'VBSP', 21)):
        raise ServerError('Workshop map must be a supported Source VBSP (version 20/21)')
    for index in range(64):
        offset, length = struct.unpack_from('<ii', header, 8 + 16 * index)
        if offset < 0 or length < 0 or offset + length > size:
            raise ServerError('Workshop BSP lump exceeds the downloaded map')


def _map_files(server, payload):
    """Accept map packages, rejecting links, client-only content and other games."""
    root = Path(server.data['dir']).resolve()
    try:
        relative_root = payload.absolute().relative_to(root)
    except ValueError as exc:
        raise ServerError('Workshop map payload must be contained in the server root') from exc
    safe_server_path(server, relative_root)
    files, maps, size, count = {}, 0, 0, 0
    for directory, subdirs, names in os.walk(payload, followlinks=False):
        count += len(subdirs) + len(names)
        if count > 10000:
            raise ServerError('Workshop map package exceeds the file limit')
        if any((Path(directory) / name).is_symlink() for name in subdirs + names):
            raise ServerError('Workshop map package contains a symlink')
        for name in names:
            source = Path(directory) / name
            if not source.is_file():
                raise ServerError('Workshop map asset is not a regular file')
            relative = source.relative_to(payload)
            if len(relative.parts) == 1 and source.suffix == '.bsp':
                relative = Path('maps') / name
            category = relative.parts[0]
            if category in ASSETS and source.suffix.lower() in ('.jpg', '.png', '.smd', '.qc'):
                continue  # Uploader/editor sources are not native runtime assets.
            if category not in ASSETS or source.suffix.lower() not in ASSETS[category]:
                if category in ('README.md', 'LICENSE', 'LICENSE.txt', 'addoninfo.txt'):
                    continue
                raise ServerError(f'Unsupported dedicated map asset: {relative}')
            if category == 'data' and (len(relative.parts) < 3 or relative.parts[1] != 'maps'):
                raise ServerError('Only native data/maps metadata is supported')
            if source.suffix == '.bsp':
                if category != 'maps' or len(relative.parts) != 2 or not MAP_NAME.fullmatch(name):
                    raise ServerError('Workshop map belongs to a different Source map family')
                _map_header(source)
                maps += 1
            size += source.stat().st_size
            if source.stat().st_size > 512 * 1024 * 1024 or size > 4 * 1024**3:
                raise ServerError('Workshop map package exceeds the size limit')
            files[f'{GAME_DIR}/{relative.as_posix()}'] = source
    if not maps:
        raise ServerError('Workshop item contains no dedicated Source map')
    return files


def apply_workshop(server, item_ids):
    """Stage native game assets; engine execution is verified separately."""
    payloads = download_workshop_items(server, WORKSHOP_APP_ID, item_ids) if item_ids else {}
    files = {}
    for item in item_ids:
        fresh = _map_files(server, payloads[item])
        if set(files).intersection(fresh):
            raise ServerError('Workshop map items collide at the same native asset path')
        files.update(fresh)
    return publish_owned_payloads(server, OWNER, files)
