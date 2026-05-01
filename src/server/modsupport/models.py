"""Data models for curated mod-support state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CuratedRelease:  # pylint: disable=too-many-instance-attributes
    family: str
    channel: str
    resolved_id: str
    url: str
    hosts: tuple[str, ...]
    archive_type: str
    destinations: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    checksum: str | None = None


@dataclass(frozen=True)
class DesiredModEntry:
    source_type: str
    requested_id: str
    resolved_id: str | None = None
    channel: str | None = None


@dataclass
class InstalledModEntry:
    source_type: str
    resolved_id: str
    installed_files: list[str] = field(default_factory=list)
