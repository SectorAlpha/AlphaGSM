"""Safe download and staging helpers for curated mod archives."""

from __future__ import annotations

import hashlib
import shutil
import tarfile
import tempfile
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
    expected_checksum = None
    if checksum is not None:
        expected_checksum = _normalize_checksum(checksum)

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_handle = None
    temp_path = None

    hasher = hashlib.sha256()
    try:
        temp_handle, temp_name = tempfile.mkstemp(
            prefix=f".{target_path.name}.",
            suffix=".tmp",
            dir=target_path.parent,
        )
        temp_path = Path(temp_name)
        with urlopen(url, timeout=30) as response, open(temp_handle, "wb", closefd=True) as handle:
            while True:
                chunk = response.read(64 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                hasher.update(chunk)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise ModSupportError(f"Failed to download {url}: {exc}") from exc

    if expected_checksum is not None:
        actual = hasher.hexdigest()
        if actual != expected_checksum:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
            raise ModSupportError(f"Checksum mismatch for {url}")

    if temp_path is not None:
        temp_path.replace(target_path)
    return target_path


def extract_tarball_safe(tar_path, extract_root):
    """Extract a tarball while rejecting entries that escape the target root."""
    tar_path = Path(tar_path)
    extract_root = Path(extract_root)
    extract_root.mkdir(parents=True, exist_ok=True)
    extracted_paths = []
    resolved_extract_root = extract_root.resolve()

    try:
        with tarfile.open(tar_path) as archive:
            members = archive.getmembers()
            validated_members = []
            for member in members:
                destination = _validate_tar_member(member, resolved_extract_root)
                validated_members.append((member, destination))

            for member, destination in validated_members:
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                extracted_file = archive.extractfile(member)
                if extracted_file is None:
                    raise ModSupportError(f"Failed to extract archive member: {member.name}")
                with extracted_file, destination.open("wb") as handle:
                    shutil.copyfileobj(extracted_file, handle)
                if member.isfile():
                    extracted_paths.append(destination)
    except ModSupportError:
        raise
    except (OSError, tarfile.TarError) as exc:
        raise ModSupportError(f"Failed to extract tarball {tar_path}: {exc}") from exc

    return extracted_paths


def install_staged_tree(*, staged_root, server_root, allowed_destinations):
    """Install staged files into approved server destinations only."""
    staged_root = Path(staged_root).resolve()
    server_root = Path(server_root).resolve()
    installed_paths = []
    approved_roots = [_normalize_relative_path(path) for path in allowed_destinations]
    planned_copies = []

    for source_path in sorted(path for path in staged_root.rglob("*") if path.is_file()):
        resolved_source_path = source_path.resolve()
        try:
            resolved_source_path.relative_to(staged_root)
        except ValueError as exc:
            raise ModSupportError(
                f"Refusing to install staged file outside staging root: {source_path.relative_to(staged_root).as_posix()}"
            ) from exc
        relative_path = source_path.relative_to(staged_root)
        if not _is_allowed_destination(relative_path, approved_roots):
            raise ModSupportError(f"Refusing to install outside approved destinations: {relative_path.as_posix()}")
        planned_copies.append((source_path, server_root / relative_path))

    server_root.mkdir(parents=True, exist_ok=True)
    for source_path, destination in planned_copies:
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


def _safe_relative_destination(*, base_root, relative_path, error_prefix):
    normalized = _normalize_relative_path(relative_path)
    destination = (Path(base_root) / normalized).resolve()
    try:
        destination.relative_to(base_root)
    except ValueError as exc:
        raise ModSupportError(f"{error_prefix}: {relative_path}") from exc
    return destination


def _validate_tar_member(member, base_root):
    destination = _safe_relative_destination(
        base_root=base_root,
        relative_path=member.name,
        error_prefix="Refusing to extract unsafe archive path",
    )
    if member.issym() or member.islnk():
        raise ModSupportError(f"Refusing to extract unsafe archive member: {member.name}")
    if member.isdir():
        return destination
    if not member.isfile():
        raise ModSupportError(f"Refusing to extract unsupported archive member: {member.name}")
    return destination


def _normalize_checksum(checksum):
    checksum = str(checksum)
    if ":" in checksum:
        algorithm, digest = checksum.split(":", 1)
        if algorithm.lower() != "sha256":
            raise ModSupportError(f"Unsupported checksum algorithm: {algorithm}")
        checksum = digest
    return checksum.lower()
