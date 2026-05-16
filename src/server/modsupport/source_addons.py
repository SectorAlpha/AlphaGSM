"""Shared helpers for Source-engine addon mod management."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
from urllib.parse import urlparse

from server import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

from .downloads import (
    download_to_cache,
    extract_7z_safe,
    extract_tarball_safe,
    extract_zip_safe,
    install_staged_tree,
    stage_single_file,
)
from .errors import ModSupportError
from .models import DesiredModEntry, InstalledModEntry
from .ownership import build_owned_manifest
from .providers import (
    GAMEBANANA_ALLOWED_HOSTS,
    MODDB_ALLOWED_HOSTS,
    resolve_direct_url_entry,
    resolve_gamebanana_mod,
    resolve_moddb_entry,
    validate_workshop_id,
)
from .reconcile import reconcile_mod_state
from .registry import CuratedRegistryLoader


_ARCHIVE_URL_SUFFIXES = {
    ".7z": "7z",
    ".tar.gz": "tar",
    ".tgz": "tar",
    ".tar.bz2": "tar",
    ".tbz2": "tar",
    ".tar.xz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".zip": "zip",
}


def load_shared_source_curated_registry():
    """Load the shared curated Source-addon registry or an override file."""

    override = os.environ.get("ALPHAGSM_SOURCE_CURATED_MODS_PATH")
    if override:
        path = Path(override)
    else:
        path = Path(__file__).resolve().parents[2] / "gamemodules" / "source_curated_mods.json"
    return CuratedRegistryLoader.load(path)


def build_source_addon_mod_support(
    *,
    game_label: str,
    game_dir: str,
    cache_namespace: str,
    direct_url_suffixes: dict[str, str],
    direct_url_filename_description: str,
    allowed_destinations: tuple[str, ...] = ("addons",),
    enabled_sources: tuple[str, ...] = ("url", "gamebanana", "moddb"),
    single_file_destination: str = "addons",
    curated_registry_loader=None,
    curated_identifier_description: str = "manifest family identifier",
    extra_payload_roots: tuple[str, ...] = (),
    download_to_cache_getter=None,
    resolve_direct_url_entry_getter=None,
    resolve_gamebanana_mod_getter=None,
    resolve_moddb_entry_getter=None,
    validate_workshop_id_getter=None,
    workshop_downloader_getter=None,
    workshop_app_id: int | None = None,
    workshop_login_anonymous: bool = True,
    prefix_provider_cache_files_with_resolved_id: bool = False,
    allow_bare_addon_root: bool = False,
    bare_addon_marker_files: tuple[str, ...] = (),
    bare_addon_marker_dirs: tuple[str, ...] = (),
):
    """Return a command surface for Source-game addon management."""

    source_types = list(enabled_sources)
    if curated_registry_loader is not None and "curated" not in source_types:
        source_types.insert(0, "curated")
    source_types = tuple(source_types)
    url_suffixes = {**_ARCHIVE_URL_SUFFIXES, **direct_url_suffixes}
    allowed_destination_set = set(allowed_destinations)
    display_source_labels = [
        "manifest/curated" if source_type == "curated" else source_type
        for source_type in source_types
    ]
    supported_source_labels = ", ".join(display_source_labels)
    bare_addon_marker_file_set = set(bare_addon_marker_files)
    bare_addon_marker_dir_set = set(bare_addon_marker_dirs)
    supported_id_description = []
    if "curated" in source_types:
        supported_id_description.append(curated_identifier_description)
    if "url" in source_types:
        supported_id_description.append("download URL")
    if "gamebanana" in source_types:
        supported_id_description.append("provider item id")
    if "moddb" in source_types:
        supported_id_description.append("Mod DB page URL")
    if "workshop" in source_types:
        supported_id_description.append("workshop id")

    def _save_data(server):
        save = getattr(server.data, "save", None)
        if callable(save):
            save()

    def _download_to_cache():
        if download_to_cache_getter is not None:
            return download_to_cache_getter()
        return download_to_cache

    def _resolve_direct_url_entry():
        if resolve_direct_url_entry_getter is not None:
            return resolve_direct_url_entry_getter()
        return resolve_direct_url_entry

    def _resolve_gamebanana_mod():
        if resolve_gamebanana_mod_getter is not None:
            return resolve_gamebanana_mod_getter()
        return resolve_gamebanana_mod

    def _resolve_moddb_entry():
        if resolve_moddb_entry_getter is not None:
            return resolve_moddb_entry_getter()
        return resolve_moddb_entry

    def _validate_workshop_id():
        if validate_workshop_id_getter is not None:
            return validate_workshop_id_getter()
        return validate_workshop_id

    def _download_workshop_item():
        if workshop_downloader_getter is not None:
            return workshop_downloader_getter()
        raise ValueError("workshop source requested without a downloader getter")

    def ensure_mod_state(server):
        mods = server.data.setdefault("mods", {})
        mods.setdefault("enabled", True)
        mods.setdefault("autoapply", True)
        desired = mods.setdefault("desired", {})
        for source_type in source_types:
            desired.setdefault(source_type, [])
        mods.setdefault("installed", [])
        mods.setdefault("last_apply", None)
        mods.setdefault("errors", [])
        return mods

    def _cache_root(server) -> Path:
        return Path(server.data["dir"]) / ".alphagsm" / "mods" / cache_namespace

    def _desired_entries(server) -> list[DesiredModEntry]:
        mods = ensure_mod_state(server)
        entries = []
        if curated_registry_loader is not None and "curated" in source_types:
            curated_registry = curated_registry_loader()
            seen_curated_ids: set[str] = set()
            for entry in mods["desired"]["curated"]:
                for resolved in curated_registry.resolve_with_dependencies(
                    entry["requested_id"],
                    entry.get("channel"),
                ):
                    if resolved.resolved_id in seen_curated_ids:
                        continue
                    seen_curated_ids.add(resolved.resolved_id)
                    entries.append(
                        DesiredModEntry(
                            source_type="curated",
                            requested_id=resolved.family,
                            resolved_id=resolved.resolved_id,
                            channel=resolved.channel,
                        )
                    )
        for source_type in source_types:
            if source_type == "curated":
                continue
            entries.extend(
                DesiredModEntry(
                    source_type=source_type,
                    requested_id=(
                        entry["workshop_id"] if source_type == "workshop" else entry["requested_id"]
                    ),
                    resolved_id=(
                        entry.get("resolved_id")
                        or (f"workshop.{entry['workshop_id']}" if source_type == "workshop" else None)
                    ),
                    channel=entry.get("channel"),
                )
                for entry in mods["desired"][source_type]
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

    def _reject_duplicate_entry(mods, source_type: str, requested_id: str):
        for entry in mods["desired"][source_type]:
            existing_requested_id = entry.get("requested_id")
            if source_type == "workshop":
                existing_requested_id = entry.get("workshop_id")
            if existing_requested_id == requested_id:
                raise ServerError(
                    f"{game_label} {source_type} entry '{requested_id}' is already present in desired state"
                )

    def _reject_duplicate_curated_entry(mods, resolved_id: str):
        for entry in mods["desired"].get("curated", []):
            if entry.get("resolved_id") == resolved_id:
                raise ServerError(
                    f"{game_label} manifest entry '{resolved_id}' is already present in desired state"
                )

    def _desired_record(server, source_type: str, resolved_id: str) -> dict:
        for entry in ensure_mod_state(server)["desired"][source_type]:
            entry_resolved_id = entry.get("resolved_id")
            if entry_resolved_id is None and source_type == "workshop":
                entry_resolved_id = f"workshop.{entry['workshop_id']}"
            if entry_resolved_id == resolved_id:
                return entry
        raise ModSupportError(
            f"Missing desired-state metadata for {game_label} addon '{resolved_id}'"
        )

    def _payload_has_allowed_content(stage_root: Path) -> bool:
        for path in stage_root.rglob("*"):
            if not path.is_file():
                continue
            relative_path = path.relative_to(stage_root)
            if relative_path.parts and relative_path.parts[0] in allowed_destination_set:
                return True
        return False

    def _discover_payload_root(stage_root: Path) -> Path:
        candidates = [stage_root, stage_root / game_dir]
        candidates.extend(stage_root / root for root in extra_payload_roots)
        if stage_root.exists():
            top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
            if len(top_level_dirs) == 1:
                candidates.extend([top_level_dirs[0], top_level_dirs[0] / game_dir])
                candidates.extend(top_level_dirs[0] / root for root in extra_payload_roots)

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

    def _normalize_bare_addon_name(value: str) -> str:
        name = Path(value).name
        lowered = name.lower()
        for suffix in (
            ".tar.gz",
            ".tar.bz2",
            ".tar.xz",
            ".tgz",
            ".tbz2",
            ".txz",
            ".tar",
            ".zip",
            ".7z",
            ".gma",
        ):
            if lowered.endswith(suffix):
                name = name[: -len(suffix)]
                break
        name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-._")
        return name or "addon"

    def _payload_is_bare_addon_root(payload_root: Path) -> bool:
        if not allow_bare_addon_root:
            return False
        if any((payload_root / marker).is_file() for marker in bare_addon_marker_file_set):
            return True
        if any((payload_root / marker).is_dir() for marker in bare_addon_marker_dir_set):
            return True
        return False

    def _install_bare_addon_root(server, payload_root: Path, install_root_name: str) -> list[str]:
        server_root = Path(server.data["dir"])
        addon_root = server_root / game_dir / single_file_destination / install_root_name
        installed_paths = []
        for source_path in sorted(path for path in payload_root.rglob("*") if path.is_file()):
            relative_path = source_path.relative_to(payload_root)
            destination = addon_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            installed_paths.append(destination)
        return build_owned_manifest(server_root, installed_paths)

    def _install_staged_payload(server, stage_root: Path, install_root_name: str | None = None) -> list[str]:
        payload_root = _discover_payload_root(stage_root)
        if _payload_has_allowed_content(payload_root):
            server_root = Path(server.data["dir"])
            installed_paths = install_staged_tree(
                staged_root=payload_root,
                server_root=server_root / game_dir,
                allowed_destinations=allowed_destinations,
            )
            return build_owned_manifest(server_root, installed_paths)

        if install_root_name and _payload_is_bare_addon_root(payload_root):
            return _install_bare_addon_root(
                server,
                payload_root,
                _normalize_bare_addon_name(install_root_name),
            )

        if not _payload_has_allowed_content(payload_root):
            raise ModSupportError(
                f"No {game_label} addon content was found in the downloaded payload"
            )
        return []

    def _extract_archive(archive_path: Path, stage_root: Path, archive_type: str):
        if archive_type == "zip":
            extract_zip_safe(archive_path, stage_root)
        elif archive_type == "7z":
            extract_7z_safe(archive_path, stage_root)
        else:
            extract_tarball_safe(archive_path, stage_root)

    def _filename_from_url(url: str, *, fallback_name: str) -> str:
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        return filename or fallback_name

    def _install_url_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        desired_record = _desired_record(server, "url", desired_entry.resolved_id)
        cache_root = _cache_root(server) / "url"
        cache_root.mkdir(parents=True, exist_ok=True)
        archive_path = cache_root / desired_record["filename"]
        _download_to_cache()(
            desired_record["download_url"],
            allowed_hosts=(desired_record["allowed_host"],),
            target_path=archive_path,
        )
        stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        if desired_record["archive_type"] == "single":
            stage_single_file(
                archive_path,
                stage_root,
                f"{single_file_destination}/{desired_record['filename']}",
            )
        else:
            _extract_archive(archive_path, stage_root, desired_record["archive_type"])
        return InstalledModEntry(
            source_type="url",
            resolved_id=desired_entry.resolved_id,
            installed_files=_install_staged_payload(server, stage_root, desired_record["filename"]),
        )

    def _install_curated_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        resolved = curated_registry_loader().resolve(
            desired_entry.requested_id,
            desired_entry.channel,
        )
        cache_root = _cache_root(server) / "curated"
        cache_root.mkdir(parents=True, exist_ok=True)
        if resolved.archive_type == "single":
            archive_name = _filename_from_url(
                resolved.url,
                fallback_name=f"{resolved.resolved_id}.{single_file_destination}",
            )
        else:
            archive_suffix = resolved.archive_type.replace(".", "_")
            archive_name = f"{resolved.resolved_id}.{archive_suffix}"
        archive_path = cache_root / archive_name
        _download_to_cache()(
            resolved.url,
            allowed_hosts=list(resolved.hosts),
            target_path=archive_path,
            checksum=resolved.checksum,
        )
        stage_root = cache_root / f"{resolved.resolved_id}_stage"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        if resolved.archive_type == "single":
            stage_single_file(
                archive_path,
                stage_root,
                f"{single_file_destination}/{archive_name}",
            )
        else:
            _extract_archive(archive_path, stage_root, resolved.archive_type)
        return InstalledModEntry(
            source_type="curated",
            resolved_id=resolved.resolved_id,
            installed_files=_install_staged_payload(server, stage_root, desired_entry.requested_id),
        )

    def _install_gamebanana_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        desired_record = _desired_record(server, "gamebanana", desired_entry.resolved_id)
        cache_root = _cache_root(server) / "gamebanana"
        cache_root.mkdir(parents=True, exist_ok=True)
        archive_name = Path(desired_record["filename"]).name
        if prefix_provider_cache_files_with_resolved_id:
            archive_name = f"{desired_entry.resolved_id}-{archive_name}"
        archive_path = cache_root / archive_name
        _download_to_cache()(
            desired_record["download_url"],
            allowed_hosts=GAMEBANANA_ALLOWED_HOSTS,
            target_path=archive_path,
        )
        stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        _extract_archive(archive_path, stage_root, desired_record["archive_type"])
        return InstalledModEntry(
            source_type="gamebanana",
            resolved_id=desired_entry.resolved_id,
            installed_files=_install_staged_payload(server, stage_root, desired_record["filename"]),
        )

    def _install_moddb_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        desired_record = _desired_record(server, "moddb", desired_entry.resolved_id)
        cache_root = _cache_root(server) / "moddb"
        cache_root.mkdir(parents=True, exist_ok=True)
        archive_name = Path(desired_record["filename"]).name
        if prefix_provider_cache_files_with_resolved_id:
            archive_name = f"{desired_entry.resolved_id}-{archive_name}"
        archive_path = cache_root / archive_name
        _download_to_cache()(
            desired_record["download_url"],
            allowed_hosts=MODDB_ALLOWED_HOSTS,
            target_path=archive_path,
        )
        stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        _extract_archive(archive_path, stage_root, desired_record["archive_type"])
        return InstalledModEntry(
            source_type="moddb",
            resolved_id=desired_entry.resolved_id,
            installed_files=_install_staged_payload(server, stage_root, desired_record["filename"]),
        )

    def _install_workshop_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        workshop_id = _validate_workshop_id()(desired_entry.requested_id)
        cache_root = _cache_root(server) / "workshop" / workshop_id
        stage_root = Path(
            _download_workshop_item()(
                cache_root,
                workshop_app_id,
                workshop_id,
                workshop_login_anonymous,
            )
        )
        return InstalledModEntry(
            source_type="workshop",
            resolved_id=desired_entry.resolved_id,
            installed_files=_install_staged_payload(server, stage_root, desired_entry.requested_id),
        )

    def _install_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        if desired_entry.source_type == "curated":
            return _install_curated_entry(server, desired_entry)
        if desired_entry.source_type == "url":
            return _install_url_entry(server, desired_entry)
        if desired_entry.source_type == "gamebanana":
            return _install_gamebanana_entry(server, desired_entry)
        if desired_entry.source_type == "moddb":
            return _install_moddb_entry(server, desired_entry)
        if desired_entry.source_type == "workshop":
            return _install_workshop_entry(server, desired_entry)
        raise ModSupportError(
            f"Unsupported {game_label} addon source: {desired_entry.source_type}"
        )

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
        mods = ensure_mod_state(server)
        for installed_entry in _installed_entries(server):
            _remove_owned_entry(server, installed_entry)
        shutil.rmtree(_cache_root(server), ignore_errors=True)
        mods["desired"] = {source_type: [] for source_type in source_types}
        mods["installed"] = []
        mods["last_apply"] = "cleanup"
        mods["errors"] = []
        _save_data(server)

    def apply_configured_mods(server):
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
            _save_data(server)
            if isinstance(exc, ServerError):
                raise
            raise ServerError(str(exc)) from exc
        mods["installed"] = _serialize_installed_entries(reconciled)
        mods["last_apply"] = "success"
        mods["errors"] = []
        _save_data(server)

    def mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
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
        if action == "add" and source == "curated" and curated_registry_loader is not None:
            if not identifier:
                raise ServerError(
                    f"{game_label} mod add curated requires a {curated_identifier_description}"
                )
            try:
                resolved = curated_registry_loader().resolve(identifier, extra)
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
            _save_data(server)
            return
        if action == "add" and source == "url" and "url" in source_types:
            if not identifier:
                raise ServerError(f"{game_label} mod add url requires a direct addon URL")
            resolved = _resolve_direct_url_entry()(
                identifier,
                filename=extra,
                allowed_suffixes=url_suffixes,
                entry_label=f"{game_label} addon URLs",
                filename_description=direct_url_filename_description,
            )
            _reject_duplicate_entry(mods, "url", resolved["requested_id"])
            mods["desired"]["url"].append(resolved)
            _save_data(server)
            return
        if action == "add" and source == "gamebanana" and "gamebanana" in source_types:
            if not identifier:
                raise ServerError(
                    f"{game_label} mod add gamebanana requires a numeric GameBanana item id"
                )
            try:
                resolved = _resolve_gamebanana_mod()(identifier)
            except ModSupportError as exc:
                raise ServerError(str(exc)) from exc
            _reject_duplicate_entry(mods, "gamebanana", resolved["requested_id"])
            mods["desired"]["gamebanana"].append(resolved)
            _save_data(server)
            return
        if action == "add" and source == "moddb" and "moddb" in source_types:
            if not identifier:
                raise ServerError(
                    f"{game_label} mod add moddb requires a canonical Mod DB page URL"
                )
            try:
                resolved = _resolve_moddb_entry()(identifier)
            except ModSupportError as exc:
                raise ServerError(str(exc)) from exc
            _reject_duplicate_entry(mods, "moddb", resolved["requested_id"])
            mods["desired"]["moddb"].append(resolved)
            _save_data(server)
            return
        if action == "add" and source == "workshop" and "workshop" in source_types:
            if not identifier:
                raise ServerError(f"{game_label} mod add workshop requires a numeric workshop id")
            workshop_id = _validate_workshop_id()(identifier)
            _reject_duplicate_entry(mods, "workshop", workshop_id)
            mods["desired"]["workshop"].append(
                {
                    "workshop_id": workshop_id,
                    "source_type": "workshop",
                    "resolved_id": f"workshop.{workshop_id}",
                }
            )
            _save_data(server)
            return
        raise ServerError(f"Unsupported {game_label} mod command")

    command_args = {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", supported_source_labels, str),
                ArgSpec("IDENTIFIER", ", ".join(supported_id_description), str),
                ArgSpec("EXTRA", "optional manifest channel or filename override", str),
            ),
        )
    }
    command_descriptions = {
        "mod": (
            f"Manage {game_label} addons from {supported_source_labels} sources."
        )
    }
    return SimpleNamespace(
        commands=("mod",),
        command_args=command_args,
        command_descriptions=command_descriptions,
        command_functions={"mod": mod_command},
        ensure_mod_state=ensure_mod_state,
        apply_configured_mods=apply_configured_mods,
        cleanup_configured_mods=cleanup_configured_mods,
    )