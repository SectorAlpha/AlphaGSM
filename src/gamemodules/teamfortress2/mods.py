"""TF2 desired-state helpers for curated, GameBanana, and workshop mod entries."""

import os
from pathlib import Path
import shutil

from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_tarball_safe,
    extract_zip_safe,
    install_staged_tree,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.reconcile import reconcile_mod_state
from server.modsupport.registry import CuratedRegistryLoader
import utils.steamcmd as steamcmd

from .gamebanana import GAMEBANANA_ALLOWED_HOSTS, resolve_gamebanana_mod
from .layout import ALLOWED_TF2_MOD_DESTINATIONS
from .workshop import validate_workshop_id


TF2_WORKSHOP_APP_ID = 440


def ensure_mod_state(server):
    """Seed the TF2 mod datastore shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("curated", [])
    desired.setdefault("gamebanana", [])
    desired.setdefault("workshop", [])
    mods.setdefault("installed", [])
    mods.setdefault("last_apply", None)
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


def _reject_duplicate_gamebanana_entry(mods, requested_id):
    for entry in mods["desired"]["gamebanana"]:
        if entry.get("requested_id") == requested_id:
            raise ServerError(
                f"GameBanana mod '{requested_id}' is already present in desired state"
            )


def _reject_duplicate_workshop_entry(mods, workshop_id):
    for entry in mods["desired"]["workshop"]:
        if entry.get("workshop_id") == workshop_id:
            raise ServerError(
                f"Workshop item '{workshop_id}' is already present in desired state"
            )


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods"


def _desired_entries(server) -> list[DesiredModEntry]:
    mods = ensure_mod_state(server)
    entries = [
        DesiredModEntry(
            source_type="curated",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
            channel=entry.get("channel"),
        )
        for entry in mods["desired"]["curated"]
    ]
    entries.extend(
        DesiredModEntry(
            source_type="gamebanana",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
        )
        for entry in mods["desired"]["gamebanana"]
    )
    entries.extend(
        DesiredModEntry(
            source_type="workshop",
            requested_id=entry["workshop_id"],
            resolved_id=entry.get("resolved_id") or f"workshop.{entry['workshop_id']}",
        )
        for entry in mods["desired"]["workshop"]
    )
    return entries


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


def _discover_payload_root(stage_root: Path) -> Path:
    stage_root = Path(stage_root)
    candidates = [stage_root, stage_root / "tf"]
    if stage_root.exists():
        top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
        if len(top_level_dirs) == 1:
            candidates.extend([top_level_dirs[0], top_level_dirs[0] / "tf"])

    seen = set()
    for candidate in candidates:
        if not candidate.exists() or not candidate.is_dir():
            continue
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if _payload_has_allowed_content(candidate):
            return candidate

    return stage_root


def _payload_has_allowed_content(stage_root: Path) -> bool:
    stage_root = Path(stage_root)
    allowed = set(ALLOWED_TF2_MOD_DESTINATIONS)
    for path in stage_root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(stage_root)
        if relative_path.parts and relative_path.parts[0] in allowed:
            return True
    return False


def _install_staged_payload(server, stage_root: Path) -> list[str]:
    payload_root = _discover_payload_root(stage_root)
    if not _payload_has_allowed_content(payload_root):
        raise ModSupportError("No TF2 server-side mod content was found in the downloaded payload")

    server_root = Path(server.data["dir"])
    installed_paths = install_staged_tree(
        staged_root=payload_root,
        server_root=server_root / "tf",
        allowed_destinations=ALLOWED_TF2_MOD_DESTINATIONS,
    )
    return build_owned_manifest(server_root, installed_paths)


def _desired_record(server, source_type: str, resolved_id: str) -> dict:
    for entry in ensure_mod_state(server)["desired"][source_type]:
        entry_resolved_id = entry.get("resolved_id")
        if entry_resolved_id is None and source_type == "workshop":
            entry_resolved_id = f"workshop.{entry['workshop_id']}"
        if entry_resolved_id == resolved_id:
            return entry
    raise ModSupportError(f"Missing desired-state metadata for {source_type} mod '{resolved_id}'")


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
    if resolved.archive_type == "zip":
        extract_zip_safe(archive_path, stage_root)
    else:
        extract_tarball_safe(archive_path, stage_root)
    return InstalledModEntry(
        source_type="curated",
        resolved_id=resolved.resolved_id,
        installed_files=_install_staged_payload(server, stage_root),
    )


def _install_gamebanana_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    desired_record = _desired_record(server, "gamebanana", desired_entry.resolved_id)
    cache_root = _cache_root(server) / "gamebanana"
    cache_root.mkdir(parents=True, exist_ok=True)
    file_name = Path(desired_record.get("filename") or "payload").name
    archive_path = cache_root / f"{desired_entry.resolved_id}-{file_name}"
    download_to_cache(
        desired_record["download_url"],
        allowed_hosts=GAMEBANANA_ALLOWED_HOSTS,
        target_path=archive_path,
    )
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)
    if desired_record["archive_type"] == "zip":
        extract_zip_safe(archive_path, stage_root)
    else:
        extract_tarball_safe(archive_path, stage_root)
    return InstalledModEntry(
        source_type="gamebanana",
        resolved_id=desired_entry.resolved_id,
        installed_files=_install_staged_payload(server, stage_root),
    )


def _install_workshop_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    workshop_id = validate_workshop_id(desired_entry.requested_id)
    cache_root = _cache_root(server) / "workshop" / workshop_id
    stage_root = Path(
        steamcmd.download_workshop_item(
            cache_root,
            TF2_WORKSHOP_APP_ID,
            workshop_id,
            True,
        )
    )
    return InstalledModEntry(
        source_type="workshop",
        resolved_id=desired_entry.resolved_id,
        installed_files=_install_staged_payload(server, stage_root),
    )


def _install_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    if desired_entry.source_type == "curated":
        return _install_curated_entry(server, desired_entry)
    if desired_entry.source_type == "gamebanana":
        return _install_gamebanana_entry(server, desired_entry)
    if desired_entry.source_type == "workshop":
        return _install_workshop_entry(server, desired_entry)
    raise ModSupportError(f"Unsupported TF2 mod source: {desired_entry.source_type}")


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"])
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current != server_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


def cleanup_configured_mods(server):
    """Remove installed TF2 mod files and reset desired-state tracking."""

    mods = ensure_mod_state(server)
    for installed_entry in _installed_entries(server):
        _remove_owned_entry(server, installed_entry)
    shutil.rmtree(_cache_root(server), ignore_errors=True)
    mods["desired"] = {"curated": [], "gamebanana": [], "workshop": []}
    mods["installed"] = []
    mods["last_apply"] = "cleanup"
    mods["errors"] = []
    server.data.save()


def apply_configured_mods(server):
    """Reconcile the configured TF2 curated mods into the server install."""

    mods = ensure_mod_state(server)
    if not mods.get("enabled", True):
        return
    try:
        reconciled = reconcile_mod_state(
            desired=_desired_entries(server),
            installed=_installed_entries(server),
            install_entry=lambda entry: _install_entry(server, entry),
            remove_entry=lambda entry: _remove_owned_entry(server, entry),
        )
    except (ModSupportError, ServerError) as exc:
        mods["errors"] = [str(exc)]
        server.data.save()
        if isinstance(exc, ServerError):
            raise
        raise ServerError(str(exc)) from exc
    mods["installed"] = _serialize_installed_entries(reconciled)
    mods["last_apply"] = "success"
    mods["errors"] = []
    server.data.save()


def tf2_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the TF2 ``mod`` command desired-state subcommands."""

    del kwargs
    mods = ensure_mod_state(server)
    if source == "manifest":
        source = "curated"
    if action == "list":
        print(mods)
        return
    if action == "apply":
        apply_configured_mods(server)
        return
    if action == "cleanup":
        cleanup_configured_mods(server)
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
    if action == "add" and source == "gamebanana":
        if not identifier:
            raise ServerError("TF2 mod add gamebanana requires a numeric GameBanana item id")
        try:
            resolved = resolve_gamebanana_mod(identifier)
        except ModSupportError as exc:
            raise ServerError(str(exc)) from exc
        _reject_duplicate_gamebanana_entry(mods, resolved["requested_id"])
        mods["desired"]["gamebanana"].append(resolved)
        server.data.save()
        return
    if action == "add" and source == "workshop":
        workshop_id = validate_workshop_id(identifier)
        _reject_duplicate_workshop_entry(mods, workshop_id)
        mods["desired"]["workshop"].append(
            {
                "workshop_id": workshop_id,
                "source_type": "workshop",
                "resolved_id": f"workshop.{workshop_id}",
            }
        )
        server.data.save()
        return
    raise ServerError("Unsupported TF2 mod command")
