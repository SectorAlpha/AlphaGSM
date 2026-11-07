"""NS2 native hexadecimal mod IDs with ownership of map-cycle additions."""

import json
import re

from server import ServerError
from server.modsupport.native_workshop import safe_server_path, write_managed_text

WORKSHOP_APP_ID = 4920
OWNER = 'ns2_workshop'


def _configuration_path(server):
    if not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', server.name) or server.name in ('.', '..'):
        raise ServerError('NS2 configuration name must be a contained server directory')
    return f'{server.name}/MapCycle.json'


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ServerError('NS2 map cycle contains duplicate JSON fields')
        result[key] = value
    return result


def _read(server, relative):
    path = safe_server_path(server, relative)
    if not path.exists():
        return None, None
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ServerError('NS2 map cycle must be a bounded regular JSON file')
    original = path.read_text(encoding='utf-8')
    try:
        body = json.loads(original, object_pairs_hook=_pairs)
    except (ValueError, TypeError) as exc:
        raise ServerError('Invalid NS2 map-cycle JSON') from exc
    if not isinstance(body, dict) or not isinstance(body.get('mods', []), list):
        raise ServerError('NS2 map-cycle mods must be an array')
    for item in body.get('mods', []):
        _hex_id(item)
    return original, body


def _hex_id(value):
    if isinstance(value, int) and not isinstance(value, bool) and 0 < value < 2**64:
        return format(value, 'x')
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{1,16}', value) or int(value, 16) == 0:
        raise ServerError('NS2 map-cycle mods require positive hexadecimal IDs')
    return value.lower()


def get_native_mod_ids(server):
    """Include operator and managed mods for the initial map's native loader."""
    _, body = _read(server, _configuration_path(server))
    return list(dict.fromkeys(_hex_id(item) for item in body.get('mods', []))) if body else []


def apply_workshop(server, item_ids):
    """Change only owned IDs, preserving operator rotation and mod settings."""
    relative = _configuration_path(server)
    previous = server.data.get(OWNER, {})
    if previous and previous.get('path') != relative:
        raise ServerError('Clean up the prior NS2 Workshop configuration before renaming the server')
    original, body = _read(server, relative)
    if body is None and not item_ids:
        # An operator may delete the config; cleanup must still release stale ownership.
        server.data.pop(OWNER, None)
        try:
            saver = getattr(server.data, 'save', None)
            if callable(saver):
                saver()
        except BaseException:
            if previous:
                server.data[OWNER] = previous
            raise
        return []
    pristine = {'maps': [server.data.get('startmap', 'ns2_summit')], 'mode': 'order', 'time': 30}
    body = dict(body) if body is not None else dict(pristine)
    had_mods = previous.get('had_mods', 'mods' in body)
    created = previous.get('created', original is None)
    owned = previous.get('added_ids', [])
    operator = [item for item in body.get('mods', []) if not isinstance(item, str) or item not in owned]
    existing = {_hex_id(item) for item in operator}
    additions = [format(int(item), 'x') for item in item_ids if format(int(item), 'x') not in existing]
    if operator or additions or had_mods:
        body['mods'] = operator + additions
    else:
        body.pop('mods', None)
    remove = created and not operator and not additions and body == previous.get('pristine', pristine)
    text = None if remove else json.dumps(body, indent=2) + '\n'
    state = {'path': relative, 'added_ids': additions, 'created': created,
             'had_mods': had_mods, 'pristine': previous.get('pristine', pristine)}
    try:
        if text is None:
            safe_server_path(server, relative).unlink(missing_ok=True)
        elif text != original:
            write_managed_text(server, relative, text)
        if additions:
            server.data[OWNER] = state
        else:
            server.data.pop(OWNER, None)
        saver = getattr(server.data, 'save', None)
        if callable(saver):
            saver()
    except BaseException:
        if previous:
            server.data[OWNER] = previous
        else:
            server.data.pop(OWNER, None)
        if original is None:
            safe_server_path(server, relative).unlink(missing_ok=True)
        else:
            write_managed_text(server, relative, original)
        raise
    return [relative] if safe_server_path(server, relative).exists() else []
