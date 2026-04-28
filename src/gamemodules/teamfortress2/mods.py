"""TF2 desired-state helpers for curated and workshop mod entries."""

import os
from pathlib import Path
import shutil

from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_tarball_safe,
    install_staged_tree,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.reconcile import reconcile_mod_state
from server.modsupport.registry import CuratedRegistryLoader

from .layout import ALLOWED_TF2_DESTINATIONS
from .workshop import raise_experimental_workshop_apply_error, validate_workshop_id


def ensure_mod_state(server):
    """Seed the TF2 mod datastore shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("curated", [])
    desired.setdefault("workshop", [])
    mods.setdefault("installed", [])
    mods.setdefault("errors", [])
    return mods


def load_tf2_curated_registry():
    """Load the checked-in TF2 curated registry or an override file."""

    override = os.environ.get("ALPHAGSM_TF2_CURATED_REGISTRY_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


def _reject_duplicate_curated_entry(mods, resolved_id):
    for entry in mods["desired"]["curated"]:
        if entry.get("resolved_id") == resolved_id:
            raise ServerError(f"Curated mod '{resolved_id}' is already present in desired state")


def _reject_duplicate_workshop_entry(mods, workshop_id):
    for entry in mods["desired"]["workshop"]:
        if entry.get("workshop_id") == workshop_id:
            raise ServerError(
                f"Workshop item '{workshop_id}' is already present in desired state"
            )


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods"


def _desired_curated_entries(server) -> list[DesiredModEntry]:
    return [
        DesiredModEntry(
            source_type="curated",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
            channel=entry.get("channel"),
        )
        for entry in ensure_mod_state(server)["desired"]["curated"]
    ]


def _installed_entries(server) -> list[InstalledModEntry]:
    return [
        InstalledModEntry(
            source_type=entry["source_type"],
            resolved_id=entry["resolved_id"],
            installed_files=list(entry.get("installed_files", [])),
        )
        for entry in ensure_mod_state(server).get("installed", [])
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


def _install_curated_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    resolved = load_tf2_curated_registry().resolve(
        desired_entry.requested_id,
        desired_entry.channel,
    )
    cache_root = _cache_root(server)
    cache_root.mkdir(parents=True, exist_ok=True)
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
    extract_tarball_safe(archive_path, stage_root)
    installed_paths = install_staged_tree(
        staged_root=stage_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=tuple(
            destination
            for destination in resolved.destinations
            if destination in ALLOWED_TF2_DESTINATIONS
        ),
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


def apply_configured_mods(server):
    """Reconcile the configured TF2 curated mods into the server install."""

    mods = ensure_mod_state(server)
    if not mods.get("enabled", True):
        return
    if mods["desired"]["workshop"]:
        raise_experimental_workshop_apply_error()
    try:
        reconciled = reconcile_mod_state(
            desired=_desired_curated_entries(server),
            installed=_installed_entries(server),
            install_entry=lambda entry: _install_curated_entry(server, entry),
            remove_entry=lambda entry: _remove_owned_entry(server, entry),
        )
    except ModSupportError as exc:
        raise ServerError(str(exc)) from exc
    mods["installed"] = _serialize_installed_entries(reconciled)
    mods["errors"] = []
    server.data.save()


def tf2_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the TF2 ``mod`` command desired-state subcommands."""

    del kwargs
    mods = ensure_mod_state(server)
    if action == "list":
        print(mods)
        return
    if action == "apply":
        apply_configured_mods(server)
        return
    if action == "add" and source == "curated":
        if not identifier:
            raise ServerError("TF2 mod add curated requires a curated family identifier")
        try:
            resolved = load_tf2_curated_registry().resolve(identifier, extra)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        _reject_duplicate_curated_entry(mods, resolved.resolved_id)
        mods["desired"]["curated"].append(
            {
                "requested_id": identifier,
                "channel": resolved.channel,
                "resolved_id": resolved.resolved_id,
            }
        )
        server.data.save()
        return
    if action == "add" and source == "workshop":
        workshop_id = validate_workshop_id(identifier)
        _reject_duplicate_workshop_entry(mods, workshop_id)
        mods["desired"]["workshop"].append(
            {"workshop_id": workshop_id, "source_type": "workshop"}
        )
        server.data.save()
        return
    raise ServerError("Unsupported TF2 mod command")
