"""Curated mod-support registry loading and resolution."""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Sequence

from .errors import ModSupportError
from .models import CuratedRelease


class CuratedRegistry:
    """Resolve curated family/channel pairs into concrete releases."""

    def __init__(self, families: dict[str, dict]):
        self.families = dict(families)

    def resolve(self, family: str, channel: str | None = None) -> CuratedRelease:
        family_payload = self.families.get(family)
        if family_payload is None:
            raise ModSupportError(f"Unknown curated mod family: {family}")
        if not isinstance(family_payload, dict):
            raise ModSupportError(f"Malformed curated mod family payload: {family}")

        resolved_channel = channel or family_payload.get("default")
        releases = family_payload.get("releases", {})
        if not isinstance(releases, dict):
            raise ModSupportError(f"Malformed curated mod family payload: {family}")

        release_payload = releases.get(resolved_channel)
        if release_payload is None:
            raise ModSupportError(
                f"Unknown curated mod release: {family}"
                + ("" if resolved_channel is None else f".{resolved_channel}")
            )
        if not isinstance(release_payload, dict):
            raise ModSupportError(f"Malformed curated mod release payload: {family}.{resolved_channel}")

        try:
            hosts = _coerce_string_sequence(
                release_payload["hosts"],
                field_name="hosts",
                release_id=f"{family}.{resolved_channel}",
            )
            destinations = _coerce_string_sequence(
                release_payload["destinations"],
                field_name="destinations",
                release_id=f"{family}.{resolved_channel}",
            )
            return CuratedRelease(
                family=family,
                channel=resolved_channel,
                resolved_id=f"{family}.{resolved_channel}",
                url=release_payload["url"],
                hosts=hosts,
                archive_type=release_payload["archive_type"],
                destinations=destinations,
                checksum=release_payload.get("checksum"),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ModSupportError(
                f"Malformed curated mod release payload: {family}.{resolved_channel}"
            ) from exc


class CuratedRegistryLoader:
    """Load a curated registry from JSON on disk."""

    @classmethod
    def load(cls, path: str | Path) -> CuratedRegistry:
        registry_path = Path(path)
        try:
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ModSupportError(
                f"Malformed curated registry JSON in {registry_path}: invalid JSON syntax"
            ) from exc
        if not isinstance(payload, dict):
            raise ModSupportError(
                f"Malformed curated registry wrapper in {registry_path}: expected top-level object"
            )

        families = payload.get("families")
        if not isinstance(families, dict):
            raise ModSupportError(
                f"Malformed curated registry wrapper in {registry_path}: expected 'families' object"
            )

        return CuratedRegistry(dict(families))


def _coerce_string_sequence(value, *, field_name: str, release_id: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ModSupportError(
            f"Malformed curated mod release payload: {release_id} field '{field_name}'"
            " must be a sequence of strings"
        )
    if not all(isinstance(item, str) for item in value):
        raise ModSupportError(
            f"Malformed curated mod release payload: {release_id} field '{field_name}'"
            " must be a sequence of strings"
        )
    return tuple(value)
