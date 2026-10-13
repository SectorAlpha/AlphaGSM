"""Owned DST download declarations and per-shard native Lua configuration."""

from pathlib import Path

from server.errors import ServerError
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from server.modsupport.workshop import validate_workshop_identifier

MAX_CONFIG_BYTES = 1024 * 1024


def _read_config(server, relative):
    path = safe_server_path(server, relative)
    if not path.exists():
        return None
    with path.open('rb') as handle:
        raw = handle.read(MAX_CONFIG_BYTES + 1)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ServerError('DST Workshop configuration exceeds the size limit')
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ServerError('DST Workshop configuration must be UTF-8 text') from exc


def _shard_config_path(server):
    parts = [server.data.get('confdir', 'DoNotStarveTogether'),
             server.data.get('cluster', server.name), server.data.get('shard', 'Master')]
    if any(not isinstance(part, str) or part in ('', '.', '..') or '/' in part or '\\' in part
           or any(ord(character) < 32 for character in part) for part in parts):
        raise ServerError('DST confdir, cluster and shard must be contained directory names')
    return str(Path(*parts) / 'modoverrides.lua')


def _overrides_text(original, item_ids):
    text = ('-- AlphaGSM managed Workshop overrides; preserve operator configuration below.\n'
            'local alphagsm_overrides = (function()\n' + (original or 'return {}\n') +
            '\nend)()\n'
            'if type(alphagsm_overrides) ~= "table" then error("modoverrides must return a table") end\n')
    for item_id in item_ids:
        key = f'workshop-{item_id}'
        text += (f'alphagsm_overrides["{key}"] = alphagsm_overrides["{key}"] or {{}}\n'
                 f'alphagsm_overrides["{key}"].enabled = true\n')
    return text + 'return alphagsm_overrides\n'


def _publish_configs(server, changes, current):
    """Restore earlier files when a later native config cannot be published."""
    written = []
    try:
        for relative, text in changes.items():
            if text is None:
                safe_server_path(server, relative).unlink(missing_ok=True)
            else:
                write_managed_text(server, relative, text)
            written.append(relative)
    except (OSError, ServerError) as exc:
        failures = []
        for relative in reversed(written):
            try:
                if current[relative] is None:
                    safe_server_path(server, relative).unlink(missing_ok=True)
                else:
                    write_managed_text(server, relative, current[relative])
            except (OSError, ServerError):
                failures.append(relative)
        if failures:
            raise ServerError(f'DST config publication failed; restore managed files: {failures}') from exc
        raise


def apply_workshop_configuration(server, item_ids):
    """Enable exact managed items while retaining and restoring operator Lua."""
    item_ids = [validate_workshop_identifier(item) for item in item_ids]
    mods = server.data.setdefault('mods', {})
    records = mods.get('dst_workshop_files', {})
    selected = ['mods/dedicated_server_mods_setup.lua', _shard_config_path(server)] if item_ids else []
    paths = list(dict.fromkeys([*records, *selected]))
    current = {relative: _read_config(server, relative) for relative in paths}
    for relative, record in records.items():
        if current[relative] != record['managed']:
            raise ServerError(f'DST managed Workshop config changed outside AlphaGSM: {relative}')
    changes, next_records = {}, {}
    for relative in paths:
        original = records[relative]['original'] if relative in records else current[relative]
        if relative not in selected:
            changes[relative] = original
            continue
        if relative.startswith('mods/'):
            text = (original or '') + '\n-- AlphaGSM Workshop downloads\n'
            text += ''.join(f'ServerModSetup("{item}")\n' for item in item_ids)
        else:
            text = _overrides_text(original, item_ids)
        if len(text.encode('utf-8')) > MAX_CONFIG_BYTES:
            raise ServerError('DST generated Workshop configuration exceeds the size limit')
        changes[relative] = text
        next_records[relative] = {'original': original, 'managed': text}
    _publish_configs(server, changes, current)
    mods['dst_workshop_files'] = next_records
    return selected
