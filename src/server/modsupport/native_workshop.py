"""Validated Workshop desired state for engines with native addon loaders."""

import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace

from server.errors import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from .errors import ModSupportError
from . import workshop


def safe_server_path(server, relative):
    """Resolve a contained config path and reject every symlink ancestor."""
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ServerError('Native Workshop configuration path must be relative and contained')
    directory = server.data.get('dir')
    if not directory:
        raise ServerError('Configure the server installation directory first')
    root = Path(directory).resolve()
    destination = root / path
    current = destination
    while current != root:
        if current.is_symlink():
            raise ServerError('Refusing native Workshop configuration through a symlink')
        current = current.parent
    try:
        destination.resolve().relative_to(root)
    except ValueError as exc:
        raise ServerError('Native Workshop configuration is outside the server root') from exc
    return destination


def write_managed_text(server, relative, text):
    """Atomically publish native config without truncating an existing file."""
    destination = safe_server_path(server, relative)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if destination.exists():
            temporary.chmod(destination.stat().st_mode & 0o777)
        safe_server_path(server, relative)
        temporary.replace(destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return destination


def apply_managed_workshop_list(server, relative, item_ids):
    """Merge native subscription IDs while retaining operator lines and ownership.

    Only canonical lines previously added here are removed. An operator who adds
    a comment or changes whitespace on such a line takes ownership of that line.
    Engine-downloaded caches are deliberately outside this configuration owner.
    """
    item_ids = list(dict.fromkeys(workshop.normalize_workshop_identifier(value) for value in item_ids))
    destination = safe_server_path(server, relative)
    if destination.exists() and (not destination.is_file() or destination.stat().st_size > 1024 * 1024):
        raise ServerError('Workshop subscription list must be a regular file under 1 MiB')
    original = destination.read_bytes().decode('utf-8') if destination.exists() else ''
    owners = server.data.setdefault('mods', {}).setdefault('native_workshop_lists', {})
    key = Path(relative).as_posix()
    previous = owners.get(key, {})
    owned_ids = set(previous.get('added_ids', []))
    lines = [line for line in original.splitlines(keepends=True) if line.rstrip('\r\n') not in owned_ids]
    existing_ids = set()
    for line in lines:
        match = re.fullmatch(r'\s*(\d+)\s*(?://[^\r\n]*|#[^\r\n]*)?', line.rstrip('\r\n'))
        if match:
            existing_ids.add(match.group(1))
    additions = [item for item in item_ids if item not in existing_ids]
    text = ''.join(lines)
    if text and additions and not text.endswith(('\r', '\n')):
        text += '\n'
    text += ''.join(f'{item}\n' for item in additions)
    created = previous.get('created', not destination.exists())
    if text != original:
        if not text and created:
            safe_server_path(server, relative).unlink(missing_ok=True)
        else:
            write_managed_text(server, relative, text)
    if additions:
        owners[key] = {'added_ids': additions, 'created': created}
    else:
        owners.pop(key, None)
    return [key] if destination.exists() else []


def build_native_workshop_support(*, game_label, workshop_app_id, apply_callback):
    """Build commands; native configuration alone never claims an engine load."""
    def save(server):
        saver = getattr(server.data, 'save', None)
        if callable(saver):
            saver()

    def ensure_mod_state(server):
        mods = server.data.setdefault('mods', {})
        mods.setdefault('enabled', True)
        mods.setdefault('autoapply', True)
        mods.setdefault('desired', {}).setdefault('workshop', [])
        mods.setdefault('installed', [])
        mods.setdefault('errors', [])
        mods.setdefault('last_apply', None)
        return mods

    def configure_items(server, item_ids):
        mods = ensure_mod_state(server)
        try:
            item_ids = list(dict.fromkeys(workshop.normalize_workshop_identifier(value) for value in item_ids))
            if item_ids:
                workshop.resolve_workshop_items(item_ids, workshop_app_id)
            paths = apply_callback(server, item_ids) or []
            for path in paths:
                safe_server_path(server, path)
        except (ModSupportError, ServerError, OSError, ValueError, RuntimeError) as exc:
            mods['errors'] = [str(exc)]
            save(server)
            raise ServerError(str(exc)) from exc
        mods['native_workshop'] = {
            'workshop_ids': item_ids, 'config_files': list(paths), 'status': 'configured',
        }
        mods['last_apply'] = 'configured'
        mods['errors'] = []
        save(server)

    def apply_configured_mods(server):
        mods = ensure_mod_state(server)
        item_ids = [entry['workshop_id'] for entry in mods['desired']['workshop']] if mods['enabled'] else []
        configure_items(server, item_ids)

    def cleanup_configured_mods(server):
        configure_items(server, [])
        ensure_mod_state(server)['desired']['workshop'].clear()
        save(server)

    def mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
        del extra, kwargs
        mods = ensure_mod_state(server)
        if action == 'list':
            print(mods)
            return
        if action == 'apply':
            apply_configured_mods(server)
            return
        if action == 'cleanup':
            cleanup_configured_mods(server)
            return
        if action not in ('add', 'remove') or source not in ('workshop', 'workshop-collection'):
            raise ServerError(f'Unsupported {game_label} mod command')
        try:
            value = workshop.normalize_workshop_identifier(identifier)
            desired = mods['desired']['workshop']
            if action == 'remove':
                if source != 'workshop':
                    raise ModSupportError('Remove expanded collection items individually with remove workshop')
                remaining = [entry for entry in desired if entry['workshop_id'] != value]
                if len(remaining) == len(desired):
                    raise ModSupportError(f'Workshop item {value} is not in desired state')
                desired[:] = remaining
            elif source == 'workshop':
                entry = workshop.resolve_workshop_item(value, workshop_app_id)
                if any(record['workshop_id'] == value for record in desired):
                    raise ModSupportError(f'Workshop item {value} is already in desired state')
                desired.append(entry)
            else:
                values = workshop.resolve_workshop_collection(value, workshop_app_id)
                existing = {entry['workshop_id'] for entry in desired}
                additions = [{'workshop_id': item, 'source_type': 'workshop',
                              'resolved_id': f'workshop.{item}', 'collection_id': value}
                             for item in values if item not in existing]
                desired.extend(additions)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        save(server)

    return SimpleNamespace(
        commands=('mod',),
        command_args={'mod': CmdSpec(
            requiredarguments=(ArgSpec('ACTION', 'list, add, remove, apply, or cleanup', str),),
            optionalarguments=(ArgSpec('SOURCE', 'workshop or workshop-collection', str),
                               ArgSpec('IDENTIFIER', 'Steam Workshop ID or URL', str)),
        )},
        command_descriptions={'mod': f'Manage {game_label} native Workshop mods.'},
        command_functions={'mod': mod_command},
        ensure_mod_state=ensure_mod_state,
        apply_configured_mods=apply_configured_mods,
        cleanup_configured_mods=cleanup_configured_mods,
    )
