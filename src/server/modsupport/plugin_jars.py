"""Shared helpers for plugin-style mod management."""

from __future__ import annotations

from pathlib import Path
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
    MODDB_ALLOWED_HOSTS,
    resolve_direct_url_entry,
    resolve_moddb_entry,
)
from .reconcile import reconcile_mod_state


ALLOWED_PLUGIN_DESTINATIONS = ("plugins",)


def build_plugin_jar_mod_support(
    *,
    game_label: str,
    curated_registry_loader,
    cache_namespace: str | None = None,
    cache_namespace_getter=None,
    runtime_label_getter=None,
    download_to_cache_getter=None,
    resolve_direct_url_entry_getter=None,
    resolve_moddb_entry_getter=None,
    allowed_destinations: tuple[str, ...] = ALLOWED_PLUGIN_DESTINATIONS,
    direct_url_suffixes: dict[str, str] | None = None,
    direct_url_filename_description: str = "a plugin .jar filename",
    direct_url_requirement_description: str = "a plugin jar URL",
    direct_url_entry_label: str | None = None,
    source_identifier_description: str = "plugin family, plugin jar url, or Mod DB page URL",
    single_file_destinations: dict[str, str] | None = None,
    bare_archive_destination: str | None = None,
    bare_archive_file_suffixes: tuple[str, ...] | None = None,
    install_root_getter=None,
):
    """Return a shared command surface for plugin-style modules."""

    if cache_namespace is None and cache_namespace_getter is None:
        raise ValueError("plugin jar mod support requires a cache namespace")

    allowed_destinations = tuple(_normalize_relative_path(path) for path in allowed_destinations)
    direct_url_suffixes = dict(direct_url_suffixes or {".jar": "jar"})
    single_file_destinations = {
        archive_type: _normalize_relative_path(destination)
        for archive_type, destination in dict(single_file_destinations or {"jar": "plugins"}).items()
    }
    bare_archive_file_suffixes = tuple(bare_archive_file_suffixes or ())

    if bare_archive_destination is not None:
        bare_archive_destination = _normalize_relative_path(bare_archive_destination)
    if bare_archive_destination is not None and not _is_path_within_allowed_destinations(
        bare_archive_destination,
        allowed_destinations,
    ):
        raise ValueError("bare archive destination must be included in allowed_destinations")

    def _install_root(server) -> Path:
        if install_root_getter is not None:
            return Path(install_root_getter(server))
        return Path(server.data["dir"])

    def _runtime_label(server) -> str:
        if runtime_label_getter is not None:
            return runtime_label_getter(server)
        return game_label

    def _cache_namespace(server) -> str:
        if cache_namespace_getter is not None:
            return cache_namespace_getter(server)
        return cache_namespace

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

    def _resolve_moddb_entry():
        if resolve_moddb_entry_getter is not None:
            return resolve_moddb_entry_getter()
        return resolve_moddb_entry

    def ensure_mod_state(server):
        mods = server.data.setdefault("mods", {})
        mods.setdefault("enabled", True)
        mods.setdefault("autoapply", True)
        desired = mods.setdefault("desired", {})
        desired.setdefault("curated", [])
        desired.setdefault("url", [])
        desired.setdefault("moddb", [])
        mods.setdefault("installed", [])
        mods.setdefault("last_apply", None)
        mods.setdefault("errors", [])
        return mods

    def _cache_root(server) -> Path:
        return Path(server.data["dir"]) / ".alphagsm" / "mods" / _cache_namespace(server)

    def _curated_registry(server):
        return curated_registry_loader(server)

    def _desired_entries(server) -> list[DesiredModEntry]:
        entries = []
        curated_registry = _curated_registry(server)
        seen_curated_ids: set[str] = set()
        for entry in ensure_mod_state(server)["desired"]["curated"]:
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
        entries.extend(
            DesiredModEntry(
                source_type="url",
                requested_id=entry["requested_id"],
                resolved_id=entry.get("resolved_id"),
            )
            for entry in ensure_mod_state(server)["desired"]["url"]
        )
        entries.extend(
            DesiredModEntry(
                source_type="moddb",
                requested_id=entry["requested_id"],
                resolved_id=entry.get("resolved_id"),
            )
            for entry in ensure_mod_state(server)["desired"]["moddb"]
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

    def _desired_record(server, source_type: str, resolved_id: str) -> dict:
        for entry in ensure_mod_state(server)["desired"][source_type]:
            if entry.get("resolved_id") == resolved_id:
                return entry
        raise ModSupportError(
            f"Missing desired-state metadata for {_runtime_label(server)} plugin '{resolved_id}'"
        )

    def _is_allowed_relative_path(relative_path: Path) -> bool:
        try:
            normalized = _normalize_relative_path(relative_path)
        except ValueError:
            return False
        return _is_path_within_allowed_destinations(normalized, allowed_destinations)

    def _matches_bare_archive_suffix(path: Path) -> bool:
        lower_name = path.name.lower()
        return any(lower_name.endswith(suffix.lower()) for suffix in bare_archive_file_suffixes)

    def _has_allowed_relative_content(candidate_root: Path) -> bool:
        for path in candidate_root.rglob("*"):
            if not path.is_file():
                continue
            if _is_allowed_relative_path(path.relative_to(candidate_root)):
                return True
        return False

    def _discover_payload_root(stage_root: Path) -> Path:
        candidates = [stage_root]
        if stage_root.exists():
            top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
            if len(top_level_dirs) == 1:
                candidates.append(top_level_dirs[0])

        seen = set()
        for candidate in candidates:
            if not candidate.exists() or not candidate.is_dir():
                continue
            resolved = candidate.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            if _has_allowed_relative_content(candidate):
                return candidate
            if candidate is not stage_root:
                return candidate
        return stage_root

    def _build_installable_stage(payload_root: Path, stage_root: Path) -> Path | None:
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        for source_path in sorted(path for path in payload_root.rglob("*") if path.is_file()):
            relative_path = source_path.relative_to(payload_root)
            if _is_allowed_relative_path(relative_path):
                install_relative_path = relative_path
            elif bare_archive_destination is not None and _matches_bare_archive_suffix(relative_path):
                install_relative_path = Path(bare_archive_destination) / relative_path
            else:
                continue

            destination = install_root / install_relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            installed_any = True

        if not installed_any:
            return None
        return install_root

    def _install_staged_payload(server, stage_root: Path) -> list[str]:
        payload_root = _discover_payload_root(stage_root)
        install_root = _build_installable_stage(payload_root, stage_root)
        if install_root is None:
            raise ModSupportError(
                f"No {_runtime_label(server)} plugin content was found in the downloaded payload"
            )

        server_root = Path(server.data["dir"])
        target_root = _install_root(server).resolve()
        installed_paths = install_staged_tree(
            staged_root=install_root,
            server_root=target_root,
            allowed_destinations=allowed_destinations,
        )
        return build_owned_manifest(server_root, installed_paths)

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
        archive_type = desired_record["archive_type"]
        single_file_destination = single_file_destinations.get(archive_type)
        if single_file_destination is not None:
            stage_single_file(
                archive_path,
                stage_root,
                (single_file_destination / desired_record["filename"]).as_posix(),
            )
        elif archive_type == "zip":
            extract_zip_safe(archive_path, stage_root)
        elif archive_type == "7z":
            extract_7z_safe(archive_path, stage_root)
        elif archive_type == "tar":
            extract_tarball_safe(archive_path, stage_root)
        else:
            raise ModSupportError(
                f"Unsupported {_runtime_label(server)} url archive type: {archive_type}"
            )
        return InstalledModEntry(
            source_type="url",
            resolved_id=desired_entry.resolved_id,
            installed_files=_install_staged_payload(server, stage_root),
        )

    def _install_curated_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        resolved = _curated_registry(server).resolve(
            desired_entry.requested_id,
            desired_entry.channel,
        )
        if any(
            not _is_path_within_allowed_destinations(
                _normalize_relative_path(destination),
                allowed_destinations,
            )
            for destination in resolved.destinations
        ):
            raise ModSupportError(
                f"Unsupported {_runtime_label(server)} manifest destinations for '{resolved.resolved_id}'"
            )
        cache_root = _cache_root(server) / "curated"
        cache_root.mkdir(parents=True, exist_ok=True)
        parsed_url = urlparse(resolved.url)
        archive_name = Path(parsed_url.path).name or f"{resolved.resolved_id}.{resolved.archive_type}"
        archive_path = cache_root / archive_name
        _download_to_cache()(
            resolved.url,
            allowed_hosts=list(resolved.hosts),
            target_path=archive_path,
            checksum=resolved.checksum,
        )
        stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        single_file_destination = single_file_destinations.get(resolved.archive_type)
        if single_file_destination is not None:
            stage_single_file(
                archive_path,
                stage_root,
                (single_file_destination / archive_name).as_posix(),
            )
        elif resolved.archive_type == "zip":
            extract_zip_safe(archive_path, stage_root)
        elif resolved.archive_type == "7z":
            extract_7z_safe(archive_path, stage_root)
        else:
            extract_tarball_safe(archive_path, stage_root)
        return InstalledModEntry(
            source_type="curated",
            resolved_id=resolved.resolved_id,
            installed_files=_install_staged_payload(server, stage_root),
        )

    def _install_moddb_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        desired_record = _desired_record(server, "moddb", desired_entry.resolved_id)
        cache_root = _cache_root(server) / "moddb"
        cache_root.mkdir(parents=True, exist_ok=True)
        archive_path = cache_root / desired_record["filename"]
        _download_to_cache()(
            desired_record["download_url"],
            allowed_hosts=MODDB_ALLOWED_HOSTS,
            target_path=archive_path,
        )
        stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
        if stage_root.exists():
            shutil.rmtree(stage_root)
        if desired_record["archive_type"] == "zip":
            extract_zip_safe(archive_path, stage_root)
        elif desired_record["archive_type"] == "7z":
            extract_7z_safe(archive_path, stage_root)
        else:
            extract_tarball_safe(archive_path, stage_root)
        return InstalledModEntry(
            source_type="moddb",
            resolved_id=desired_entry.resolved_id,
            installed_files=_install_staged_payload(server, stage_root),
        )

    def _install_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
        if desired_entry.source_type == "curated":
            return _install_curated_entry(server, desired_entry)
        if desired_entry.source_type == "url":
            return _install_url_entry(server, desired_entry)
        if desired_entry.source_type == "moddb":
            return _install_moddb_entry(server, desired_entry)
        raise ModSupportError(
            f"Unsupported {_runtime_label(server)} mod source: {desired_entry.source_type}"
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
        mods["desired"] = {"curated": [], "url": [], "moddb": []}
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
        if action == "list":
            print(mods)
            return
        if action == "apply":
            apply_configured_mods(server)
            return
        if action == "cleanup":
            cleanup_configured_mods(server)
            return
        if action == "add" and source in ("manifest", "curated"):
            if not identifier:
                raise ServerError(
                    f"{_runtime_label(server)} mod add manifest requires a plugin family"
                )
            try:
                resolved = _curated_registry(server).resolve(identifier, extra)
            except ModSupportError as exc:
                raise ServerError(str(exc)) from exc
            for entry in mods["desired"]["curated"]:
                if entry.get("resolved_id") == resolved.resolved_id:
                    raise ServerError(
                        f"{_runtime_label(server)} manifest entry '{resolved.resolved_id}' is already present in desired state"
                    )
            mods["desired"]["curated"].append(
                {
                    "requested_id": identifier,
                    "resolved_id": resolved.resolved_id,
                    "channel": resolved.channel,
                }
            )
            _save_data(server)
            return
        if action == "add" and source == "url":
            if not identifier:
                raise ServerError(
                    f"{_runtime_label(server)} mod add url requires {direct_url_requirement_description}"
                )
            resolved = _resolve_direct_url_entry()(
                identifier,
                filename=extra,
                allowed_suffixes=direct_url_suffixes,
                entry_label=direct_url_entry_label or f"{_runtime_label(server)} mod url entries",
                filename_description=direct_url_filename_description,
            )
            for entry in mods["desired"]["url"]:
                if entry.get("requested_id") == resolved["requested_id"]:
                    raise ServerError(
                        f"{_runtime_label(server)} mod '{resolved['requested_id']}' is already present in desired state"
                    )
            mods["desired"]["url"].append(resolved)
            _save_data(server)
            return
        if action == "add" and source == "moddb":
            if not identifier:
                raise ServerError(
                    f"{_runtime_label(server)} mod add moddb requires a canonical Mod DB page URL"
                )
            try:
                resolved = _resolve_moddb_entry()(identifier)
            except ModSupportError as exc:
                raise ServerError(str(exc)) from exc
            for entry in mods["desired"]["moddb"]:
                if entry.get("requested_id") == resolved["requested_id"]:
                    raise ServerError(
                        f"{_runtime_label(server)} Mod DB entry '{resolved['requested_id']}' is already present in desired state"
                    )
            mods["desired"]["moddb"].append(resolved)
            _save_data(server)
            return
        raise ServerError(f"Unsupported {_runtime_label(server)} mod command")

    command_args = {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "manifest/curated, url, or moddb", str),
                ArgSpec(
                    "IDENTIFIER",
                    source_identifier_description,
                    str,
                ),
                ArgSpec("EXTRA", "optional manifest channel or plugin filename", str),
            ),
        )
    }
    command_descriptions = {
        "mod": (
            f"Manage {game_label} plugins from the local manifest, direct download URLs, or Mod DB page URLs."
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


def _normalize_relative_path(path_value) -> Path:
    path = Path(path_value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe relative path: {path_value}")
    return path


def _is_path_within_allowed_destinations(relative_path: Path, allowed_destinations: tuple[Path, ...]) -> bool:
    return any(
        relative_path == allowed_destination or allowed_destination in relative_path.parents
        for allowed_destination in allowed_destinations
    )