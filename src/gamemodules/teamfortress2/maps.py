"""TF2 desired-state helpers for curated map entries."""

import os
from pathlib import Path
import shutil

from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_tarball_safe,
    install_staged_tree,
    stage_single_file,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.reconcile import reconcile_mod_state
from server.modsupport.registry import CuratedRegistryLoader

from .layout import ALLOWED_TF2_DESTINATIONS

_BSP_ARCHIVE_TYPE = "bsp"


def ensure_map_state(server):
    """Seed the TF2 map datastore shape and return it."""

    maps = server.data.setdefault("maps", {})
    maps.setdefault("enabled", True)
    maps.setdefault("autoapply", True)
    desired = maps.setdefault("desired", {})
    desired.setdefault("curated", [])
    maps.setdefault("installed", [])
    maps.setdefault("last_apply", None)
    maps.setdefault("errors", [])
    return maps


def load_tf2_curated_map_registry():
    """Load the built-in curated map registry, or an override file.

    Set ``ALPHAGSM_TF2_CURATED_MAPS_PATH`` to an absolute path to a JSON file
    to replace the built-in ``curated_maps.json`` with your own registry.
    """

    override = os.environ.get("ALPHAGSM_TF2_CURATED_MAPS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_maps.json")
    return CuratedRegistryLoader.load(path)


def _reject_duplicate_curated_map_entry(maps, resolved_id):
    for entry in maps["desired"]["curated"]:
        if entry.get("resolved_id") == resolved_id:
            raise ServerError(f"Curated map '{resolved_id}' is already present in desired state")


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "maps"


def _desired_curated_entries(server) -> list[DesiredModEntry]:
    return [
        DesiredModEntry(
            source_type="curated",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
            channel=entry.get("channel"),
        )
        for entry in ensure_map_state(server)["desired"]["curated"]
    ]


def _installed_entries(server) -> list[InstalledModEntry]:
    return [
        InstalledModEntry(
            source_type=entry["source_type"],
            resolved_id=entry["resolved_id"],
            installed_files=list(entry.get("installed_files", [])),
        )
        for entry in ensure_map_state(server).get("installed", [])
    ]


def _serialize_installed_entries(entries: list[InstalledModEntry]) -> list[dict]:
    return [
        {
            "source_type": entry.source_type,
            "resolved_id": entry.resolved_id,
            "installed_files": list(entry.installed_files),
        }
        for entry in entries
    ]


def _install_curated_map_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    resolved = load_tf2_curated_map_registry().resolve(
        desired_entry.requested_id,
        desired_entry.channel,
    )
    cache_root = _cache_root(server)
    cache_root.mkdir(parents=True, exist_ok=True)

    if resolved.archive_type == _BSP_ARCHIVE_TYPE:
        archive_suffix = "bsp"
    else:
        archive_suffix = resolved.archive_type.replace(".", "_")
    archive_path = cache_root / f"{resolved.resolved_id}.{archive_suffix}"

    download_to_cache(
        resolved.url,
        allowed_hosts=resolved.hosts,
        target_path=archive_path,
        checksum=resolved.checksum,
    )

    stage_root = cache_root / f"{resolved.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    if resolved.archive_type == _BSP_ARCHIVE_TYPE:
        # Stage the single .bsp directly under tf/maps/ using the map family
        # name as the filename stem; install_staged_tree then picks it up.
        stage_single_file(archive_path, stage_root, f"tf/maps/{resolved.family}.bsp")
    else:
        extract_tarball_safe(archive_path, stage_root)

    allowed_dests = tuple(
        destination
        for destination in resolved.destinations
        if destination in ALLOWED_TF2_DESTINATIONS
    )
    installed_paths = install_staged_tree(
        staged_root=stage_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=allowed_dests,
    )
    return InstalledModEntry(
        source_type="curated",
        resolved_id=resolved.resolved_id,
        installed_files=build_owned_manifest(Path(server.data["dir"]), installed_paths),
    )


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"])
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()


def apply_configured_maps(server):
    """Reconcile the configured TF2 maps into the server install."""

    maps = ensure_map_state(server)
    if not maps.get("enabled", True):
        return
    try:
        reconciled = reconcile_mod_state(
            desired=_desired_curated_entries(server),
            installed=_installed_entries(server),
            install_entry=lambda entry: _install_curated_map_entry(server, entry),
            remove_entry=lambda entry: _remove_owned_entry(server, entry),
        )
    except (ModSupportError, ServerError) as exc:
        maps["errors"] = [str(exc)]
        server.data.save()
        if isinstance(exc, ServerError):
            raise
        raise ServerError(str(exc)) from exc
    maps["installed"] = _serialize_installed_entries(reconciled)
    maps["last_apply"] = "success"
    maps["errors"] = []
    server.data.save()


def tf2_map_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the TF2 ``map`` command desired-state subcommands."""

    del kwargs
    maps = ensure_map_state(server)
    if action == "list":
        print(maps)
        return
    if action == "apply":
        apply_configured_maps(server)
        return
    if action == "add" and source == "curated":
        if not identifier:
            raise ServerError("Usage: map add curated <name> [channel]")
        try:
            resolved = load_tf2_curated_map_registry().resolve(identifier, extra)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        _reject_duplicate_curated_map_entry(maps, resolved.resolved_id)
        maps["desired"]["curated"].append(
            {
                "source_type": "curated",
                "requested_id": identifier,
                "resolved_id": resolved.resolved_id,
                "channel": resolved.channel,
            }
        )
        server.data.save()
        return
    raise ServerError(f"Unknown map action: {action}")
