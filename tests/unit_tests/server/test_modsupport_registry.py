import json

import pytest

from server.modsupport.errors import ModSupportError
from server.modsupport.registry import CuratedRegistry, CuratedRegistryLoader


def _families():
    return {
        "metamod": {
            "default": "stable",
            "releases": {
                "stable": {
                    "url": "https://example.invalid/metamod-stable.zip",
                    "hosts": ["example.invalid"],
                    "archive_type": "zip",
                    "destinations": ["tf/addons"],
                }
            },
        },
        "sourcemod": {
            "default": "stable",
            "releases": {
                "stable": {
                    "url": "https://example.invalid/sourcemod-stable.zip",
                    "hosts": ["example.invalid"],
                    "archive_type": "zip",
                    "destinations": ["tf/addons"],
                    "dependencies": ["metamod"],
                },
                "1.12": {
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
    assert resolved.hosts == ("example.invalid",)
    assert resolved.destinations == ("tf/addons",)
    assert resolved.dependencies == ("metamod",)


def test_resolve_uses_explicit_channel_for_curated_family():
    registry = CuratedRegistry(_families())

    resolved = registry.resolve("sourcemod", "1.12")

    assert resolved.resolved_id == "sourcemod.1.12"


def test_resolve_rejects_unknown_family():
    registry = CuratedRegistry(_families())

    with pytest.raises(ModSupportError):
        registry.resolve("notarealfamily")


def test_resolve_rejects_unknown_release():
    registry = CuratedRegistry(_families())

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod", "snapshot")


def test_resolve_rejects_malformed_release_payload():
    families = _families()
    del families["sourcemod"]["releases"]["stable"]["hosts"]
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_string_hosts_payload():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["hosts"] = "example.invalid"
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_string_destinations_payload():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["destinations"] = "tf/addons"
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_non_string_family_default():
    families = _families()
    families["sourcemod"]["default"] = 112
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_non_string_url():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["url"] = 123
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_non_string_archive_type():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["archive_type"] = 123
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_none_archive_type():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["archive_type"] = None
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_rejects_non_string_checksum():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["checksum"] = 123
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_resolve_with_dependencies_returns_install_order():
    registry = CuratedRegistry(_families())

    resolved = registry.resolve_with_dependencies("sourcemod")

    assert [entry.resolved_id for entry in resolved] == ["metamod.stable", "sourcemod.stable"]


def test_resolve_with_dependencies_rejects_cycles():
    families = _families()
    families["metamod"]["releases"]["stable"]["dependencies"] = ["sourcemod"]
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError, match="dependency cycle"):
        registry.resolve_with_dependencies("sourcemod")


def test_resolve_rejects_non_string_dependencies_entries():
    families = _families()
    families["sourcemod"]["releases"]["stable"]["dependencies"] = [123]
    registry = CuratedRegistry(families)

    with pytest.raises(ModSupportError):
        registry.resolve("sourcemod")


def test_loader_reads_registry_json(tmp_path):
    payload = {"families": _families()}
    registry_path = tmp_path / "curated-mods.json"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    registry = CuratedRegistryLoader.load(registry_path)

    assert registry.resolve("sourcemod").resolved_id == "sourcemod.stable"


def test_loader_rejects_malformed_wrapper(tmp_path):
    registry_path = tmp_path / "curated-mods.json"
    registry_path.write_text(json.dumps({"not_families": _families()}), encoding="utf-8")

    with pytest.raises(ModSupportError, match=str(registry_path)):
        CuratedRegistryLoader.load(registry_path)


def test_loader_rejects_invalid_json_syntax(tmp_path):
    registry_path = tmp_path / "curated-mods.json"
    registry_path.write_text("{invalid-json", encoding="utf-8")

    with pytest.raises(ModSupportError, match=str(registry_path)):
        CuratedRegistryLoader.load(registry_path)
