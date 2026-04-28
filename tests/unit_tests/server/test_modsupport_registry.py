import json

import pytest

from server.modsupport.errors import ModSupportError
from server.modsupport.registry import CuratedRegistry, CuratedRegistryLoader


def _families():
    return {
        "sourcemod": {
            "default": "stable",
            "channels": {
                "stable": {
                    "resolved_id": "sourcemod.stable",
                    "url": "https://example.invalid/sourcemod-stable.zip",
                    "hosts": ["example.invalid"],
                    "archive_type": "zip",
                    "destinations": ["tf/addons"],
                },
                "1.12": {
                    "resolved_id": "sourcemod.1.12",
                    "url": "https://example.invalid/sourcemod-1.12.zip",
                    "hosts": ["example.invalid"],
                    "archive_type": "zip",
                    "destinations": ["tf/addons"],
                },
            },
        }
    }


def test_resolve_uses_default_channel_for_curated_family():
    registry = CuratedRegistry(_families())

    resolved = registry.resolve("sourcemod")

    assert resolved.resolved_id == "sourcemod.stable"


def test_resolve_uses_explicit_channel_for_curated_family():
    registry = CuratedRegistry(_families())

    resolved = registry.resolve("sourcemod", "1.12")

    assert resolved.resolved_id == "sourcemod.1.12"


def test_resolve_rejects_unknown_family():
    registry = CuratedRegistry(_families())

    with pytest.raises(ModSupportError):
        registry.resolve("metamod")


def test_loader_reads_registry_json(tmp_path):
    payload = {"families": _families()}
    registry_path = tmp_path / "curated-mods.json"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    registry = CuratedRegistryLoader.load(registry_path)

    assert registry.resolve("sourcemod").resolved_id == "sourcemod.stable"
