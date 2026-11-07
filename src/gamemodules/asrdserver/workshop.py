"""Managed native Reactive Drop Workshop config, retaining operator commands."""

from server import ServerError
from server.modsupport.native_workshop import safe_server_path, write_managed_text

WORKSHOP_APP_ID = 563560
CONFIG = 'reactivedrop/cfg/workshop.cfg'
OWNER = 'reactivedrop_workshop'
BEGIN = '// BEGIN AlphaGSM Workshop\n'
END = '// END AlphaGSM Workshop\n'


def apply_workshop(server, item_ids):
    """Merge an exact owned block into the config the native engine executes."""
    path = safe_server_path(server, CONFIG)
    if path.exists() and (not path.is_file() or path.stat().st_size > 1024 * 1024):
        raise ServerError('Reactive Drop Workshop config must be a bounded regular file')
    original = path.read_bytes().decode('utf-8') if path.exists() else None
    prior = server.data.get(OWNER, {})
    old = prior.get('block', '')
    text = original or ''
    if old:
        if text.count(old) != 1:
            raise ServerError('Managed Reactive Drop Workshop block changed externally; preserving it')
        text = text.replace(old, '', 1)
    elif BEGIN in text or END in text:
        raise ServerError('Unowned Reactive Drop Workshop block already exists')
    block = ''
    if item_ids:
        block = ('\n' if text and not text.endswith(('\n', '\r')) else '') + BEGIN
        block += ''.join(f'rd_enable_workshop_item {item}\n' for item in item_ids) + END
    updated = text + block
    created = prior.get('created', original is None)
    try:
        if not updated and created:
            path.unlink(missing_ok=True)
        elif updated != original and (updated or original is not None):
            write_managed_text(server, CONFIG, updated)
        if block:
            server.data[OWNER] = {'block': block, 'created': created}
        else:
            server.data.pop(OWNER, None)
        saver = getattr(server.data, 'save', None)
        if callable(saver):
            saver()
    except BaseException:
        if prior:
            server.data[OWNER] = prior
        else:
            server.data.pop(OWNER, None)
        if original is None:
            safe_server_path(server, CONFIG).unlink(missing_ok=True)
        else:
            write_managed_text(server, CONFIG, original)
        raise
    return [CONFIG] if path.exists() else []
