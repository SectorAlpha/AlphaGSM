"""Transactional native payload publication with exact file ownership."""

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
from tempfile import mkdtemp

from server.errors import ServerError
from .native_workshop import safe_server_path


class PayloadRecoveryError(ServerError):
    """Publication failed and its previous files require manual recovery."""


def _relative(value):
    """Require a canonical portable file path within the server."""
    if not isinstance(value, str) or '\\' in value or '\x00' in value:
        raise ServerError('Invalid owned payload path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ServerError('Owned payload path must be relative and contained')
    return path.as_posix()


def _hash_file(path):
    """Hash large mod files without loading their entire payload into memory."""
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _file_path(server, relative):
    """Reject directory targets and file ancestors before any publication."""
    path = safe_server_path(server, _relative(relative))
    root = Path(server.data['dir']).resolve()
    if path.exists() and not path.is_file():
        raise ServerError(f'Owned payload target is not a file: {relative}')
    for parent in path.parents:
        if parent == root:
            break
        if parent.exists() and not parent.is_dir():
            raise ServerError(f'Owned payload parent is not a directory: {relative}')
    return path


def _source_path(server, source):
    """Only publish regular files from the contained download/staging tree."""
    root = Path(server.data['dir']).resolve()
    try:
        relative = Path(source).absolute().relative_to(root).as_posix()
    except (TypeError, ValueError) as exc:
        raise ServerError('Owned payload source must be within the server root') from exc
    path = _file_path(server, relative)
    if not path.is_file():
        raise ServerError(f'Owned payload source is not a regular file: {relative}')
    return path


def _registry(server, owner):
    """Validate all ownership records before trusting them as deletion authority."""
    if not isinstance(owner, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]{1,80}', owner):
        raise ServerError('Invalid owned payload owner')
    registry = server.data.setdefault('mods', {}).setdefault('owned_payloads', {})
    if not isinstance(registry, dict):
        raise ServerError('Invalid owned payload registry')
    for entries in registry.values():
        if not isinstance(entries, dict):
            raise ServerError('Invalid owned payload manifest')
        for relative, digest in entries.items():
            _relative(relative)
            if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise ServerError('Invalid owned payload hash')
    return registry


def _preflight(server, owner, files, registry):
    """Check the complete batch for modifications, ownership and path aliases."""
    previous = registry.get(owner, {})
    for relative, expected in previous.items():
        path = _file_path(server, relative)
        if path.exists() and _hash_file(path) != expected:
            raise ServerError(f'Refusing to change externally modified owned payload: {relative}')
    destinations = {}
    sources = {}
    folded = set()
    other_paths = {relative.casefold() for key, entries in registry.items()
                   if key != owner for relative in entries}
    for relative, source in files.items():
        relative = _relative(relative)
        key = relative.casefold()
        if key in folded or any(key.startswith(old + '/') or old.startswith(key + '/')
                                for old in folded):
            raise ServerError('Owned payload paths overlap or differ only by case')
        folded.add(key)
        if key in other_paths or any(key.startswith(old + '/') or old.startswith(key + '/')
                                     for old in other_paths):
            raise ServerError(f'Owned payload is claimed by another owner: {relative}')
        path = _file_path(server, relative)
        if path.exists() and relative not in previous:
            raise ServerError(f'Refusing to replace unowned payload: {relative}')
        destinations[relative] = path
        sources[relative] = source if isinstance(source, bytes) else _source_path(server, source)
    return previous, destinations, sources


def _stage_sources(temporary, sources):
    """Prepare every fresh file and hash before native destinations are touched."""
    staged = {}
    hashes = {}
    for index, (relative, source) in enumerate(sources.items()):
        path = temporary / f'new-{index}'
        if isinstance(source, bytes):
            path.write_bytes(source)
        else:
            shutil.copy2(source, path)
        staged[relative] = path
        hashes[relative] = _hash_file(path)
    return staged, hashes


def _rollback(server, backups, published):
    """Restore previous files if any native publication or state save fails."""
    for relative in reversed(published):
        path = _file_path(server, relative)
        if path.exists():
            path.unlink()
    for relative, backup in reversed(list(backups.items())):
        destination = _file_path(server, relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(backup, destination)


def _publish(server, owner, registry, previous, staged, hashes, temporary):
    """Apply a batch and roll it back together with the in-memory ownership state."""
    backups = {}
    published = []
    had_owner = owner in registry
    (temporary / 'recovery.json').write_text(json.dumps({
        'owner': owner, 'files': {relative: {'backup': f'old-{index}', 'sha256': digest}
                                for index, (relative, digest) in enumerate(previous.items())}
    }, indent=2), encoding='utf-8')
    try:
        for index, relative in enumerate(previous):
            destination = _file_path(server, relative)
            if destination.exists():
                backup = temporary / f'old-{index}'
                os.replace(destination, backup)
                backups[relative] = backup
        for relative, source in staged.items():
            destination = _file_path(server, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
            published.append(relative)
        registry[owner] = hashes
        saver = getattr(server.data, 'save', None)
        if callable(saver):
            saver()
    except BaseException:
        if had_owner:
            registry[owner] = previous
        else:
            registry.pop(owner, None)
        try:
            _rollback(server, backups, published)
        except (OSError, ServerError) as exc:
            raise PayloadRecoveryError(
                f'Owned payload rollback failed; original files retained for recovery at {temporary}'
            ) from exc
        raise


def publish_owned_payloads(server, owner, files):
    """Replace this owner's files, preserving all unowned and externally edited files.

    ``files`` maps contained relative destinations to regular source Paths within
    the server root, or small generated byte payloads. Adapters must validate game
    metadata and archive contents before calling this helper. Returns owned paths;
    these paths prove staging only, never that the running engine loaded a mod.
    """
    registry = _registry(server, owner)
    previous, _destinations, sources = _preflight(server, owner, files, registry)
    scratch = safe_server_path(server, '.alphagsm/owned-payloads')
    scratch.mkdir(parents=True, exist_ok=True)
    temporary = Path(mkdtemp(prefix='.transaction-', dir=scratch))
    retain_recovery = False
    try:
        staged, hashes = _stage_sources(temporary, sources)
        _publish(server, owner, registry, previous, staged, hashes, temporary)
    except PayloadRecoveryError:
        retain_recovery = True
        raise
    finally:
        if not retain_recovery:
            shutil.rmtree(temporary)
    return list(hashes)


def cleanup_owned_payloads(server, owner):
    """Remove unchanged files belonging to this owner and retain operator extras."""
    return publish_owned_payloads(server, owner, {})
