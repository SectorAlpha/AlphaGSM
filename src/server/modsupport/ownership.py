"""Ownership helpers for installed curated mod files."""

from __future__ import annotations

from pathlib import Path

from .errors import ModSupportError


def build_owned_manifest(server_root, installed_paths):
    """Return sorted relative paths for files installed under the server root."""
    server_root = Path(server_root).resolve()
    manifest = []

    for installed_path in installed_paths:
        try:
            relative_path = Path(installed_path).resolve().relative_to(server_root)
        except ValueError as exc:
            raise ModSupportError(f"Installed path is outside server root: {installed_path}") from exc
        manifest.append(relative_path.as_posix())

    return sorted(manifest)
