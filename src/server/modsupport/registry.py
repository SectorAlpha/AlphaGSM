"""Curated mod-support registry loading and resolution."""

from __future__ import annotations

import json
from pathlib import Path

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

        resolved_channel = channel or family_payload.get("default")
        releases = family_payload.get("releases", {})
        release_payload = releases.get(resolved_channel)
        if release_payload is None:
            raise ModSupportError(
                f"Unknown curated mod release: {family}"
                + ("" if resolved_channel is None else f".{resolved_channel}")
            )

        return CuratedRelease(
            family=family,
            channel=resolved_channel,
            resolved_id=f"{family}.{resolved_channel}",
            url=release_payload["url"],
            hosts=tuple(release_payload["hosts"]),
            archive_type=release_payload["archive_type"],
            destinations=tuple(release_payload["destinations"]),
            checksum=release_payload.get("checksum"),
        )


class CuratedRegistryLoader:
    """Load a curated registry from JSON on disk."""

    @classmethod
    def load(cls, path: str | Path) -> CuratedRegistry:
        registry_path = Path(path)
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        return CuratedRegistry(dict(payload.get("families", {})))
