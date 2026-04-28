"""Safe download and staging helpers for curated mod archives."""

from __future__ import annotations

import hashlib
import shutil
import tarfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

from .errors import ModSupportError


def download_to_cache(url, *, allowed_hosts, target_path, checksum=None):
    """Download a file to cache after validating the source host and checksum."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname or hostname not in set(allowed_hosts):
        raise ModSupportError(f"Untrusted download host: {hostname or url}")

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    hasher = hashlib.sha256()
    try:
        with urlopen(url) as response, target_path.open("wb") as handle:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                hasher.update(chunk)
    except OSError as exc:
        raise ModSupportError(f"Failed to download {url}: {exc}") from exc

    if checksum is not None:
        expected = _normalize_checksum(checksum)
        actual = hasher.hexdigest()
        if actual != expected:
            target_path.unlink(missing_ok=True)
            raise ModSupportError(f"Checksum mismatch for {url}")

    return target_path


def extract_tarball_safe(tar_path, extract_root):
    """Extract a tarball while rejecting entries that escape the target root."""
    tar_path = Path(tar_path)
    extract_root = Path(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    extracted_paths = []

    try:
        with tarfile.open(tar_path) as archive:
            for member in archive.getmembers():
                destination = (extract_root / member.name).resolve()
                try:
                    destination.relative_to(extract_root.resolve())
                except ValueError as exc:
                    raise ModSupportError(f"Refusing to extract unsafe archive path: {member.name}") from exc
                archive.extract(member, extract_root)
                if member.isfile():
                    extracted_paths.append(extract_root / member.name)
    except (OSError, tarfile.TarError) as exc:
        if isinstance(exc, ModSupportError):
            raise
        raise ModSupportError(f"Failed to extract tarball {tar_path}: {exc}") from exc

    return extracted_paths


def install_staged_tree(*, staged_root, server_root, allowed_destinations):
    """Install staged files into approved server destinations only."""
    staged_root = Path(staged_root).resolve()
    server_root = Path(server_root).resolve()
    server_root.mkdir(parents=True, exist_ok=True)
    installed_paths = []
    approved_roots = [_normalize_relative_path(path) for path in allowed_destinations]

    for source_path in sorted(path for path in staged_root.rglob("*") if path.is_file()):
        relative_path = source_path.resolve().relative_to(staged_root)
        if not _is_allowed_destination(relative_path, approved_roots):
            raise ModSupportError(f"Refusing to install outside approved destinations: {relative_path.as_posix()}")

        destination = server_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        installed_paths.append(destination)

    return installed_paths


def _is_allowed_destination(relative_path, approved_roots):
    normalized = _normalize_relative_path(relative_path)
    return any(
        normalized == approved_root or approved_root in normalized.parents
        for approved_root in approved_roots
    )


def _normalize_relative_path(path_value):
    path = Path(path_value)
    if path.is_absolute() or ".." in path.parts:
        raise ModSupportError(f"Unsafe relative path: {path_value}")
    return path


def _normalize_checksum(checksum):
    checksum = str(checksum)
    if ":" in checksum:
        algorithm, digest = checksum.split(":", 1)
        if algorithm.lower() != "sha256":
            raise ModSupportError(f"Unsupported checksum algorithm: {algorithm}")
        checksum = digest
    return checksum.lower()
