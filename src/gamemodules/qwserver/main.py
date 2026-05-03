"""QuakeWorld dedicated server lifecycle helpers."""

import os
from pathlib import Path
import shutil

import screen
import server.runtime as runtime_module
from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_7z_safe,
    extract_tarball_safe,
    extract_zip_safe,
    install_staged_tree,
    stage_single_file,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.providers import resolve_direct_url_entry
from server.modsupport.reconcile import reconcile_mod_state
from server.settable_keys import build_launch_arg_values
from utils.archive_install import install_binary
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.github_releases import resolve_release_asset
from utils.gamemodules import common as gamemodule_common

MVDSV_LATEST_RELEASE_API = "https://api.github.com/repos/QW-Group/mvdsv/releases/latest"
QW_MOD_CACHE_DIRNAME = "qwserver"
QW_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".pak": "pak",
    ".tar.gz": "tar",
    ".tbz2": "tar",
    ".tgz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".tar.bz2": "tar",
    ".tar.xz": "tar",
    ".zip": "zip",
}

commands = ("mod",)
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install QuakeWorld in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "pak archive URL or direct pak URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = {
    "mod": "Manage QuakeWorld pak content from direct archive URLs or direct pak URLs into the qw content directory."
}
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        port_tokens=("-port",),
        hostname_tokens=("+hostname",),
    ),
    **gamemodule_common.build_versioned_download_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def ensure_mod_state(server):
    """Seed the QuakeWorld mod desired-state shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("url", [])
    mods.setdefault("installed", [])
    mods.setdefault("last_apply", None)
    mods.setdefault("errors", [])
    return mods


def _save_data(server):
    save = getattr(server.data, "save", None)
    if callable(save):
        save()


def _content_root(_server) -> str:
    return "qw"


def _ensure_content_backup(server):
    content_root = _content_root(server)
    backupfiles = list(server.data.setdefault("backupfiles", [content_root]))
    if content_root not in backupfiles:
        backupfiles.append(content_root)
        server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": [content_root]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault("default", {"targets": [content_root]})
    targets = list(default_profile.setdefault("targets", [content_root]))
    if content_root not in targets:
        targets.append(content_root)
        default_profile["targets"] = targets


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / QW_MOD_CACHE_DIRNAME


def _allowed_destinations(server) -> tuple[str, ...]:
    return (_content_root(server),)


def _desired_entries(server) -> list[DesiredModEntry]:
    return [
        DesiredModEntry(
            source_type="url",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
        )
        for entry in ensure_mod_state(server)["desired"]["url"]
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


def _extract_archive(archive_path: Path, stage_root: Path, archive_type: str) -> None:
    if archive_type == "zip":
        extract_zip_safe(archive_path, stage_root)
        return
    if archive_type == "7z":
        extract_7z_safe(archive_path, stage_root)
        return
    extract_tarball_safe(archive_path, stage_root)


def _pak_files(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_file() and path.name.lower().endswith(".pak")
    ]


def _build_install_stage(stage_root: Path, *, content_root: str) -> Path | None:
    candidates = [stage_root]
    if stage_root.exists():
        top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
        if len(top_level_dirs) == 1:
            candidates.append(top_level_dirs[0])

    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)

        prefixed_root = candidate / content_root
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        source_roots = []
        if prefixed_root.is_dir():
            source_roots.append(prefixed_root)
        if _pak_files(candidate):
            source_roots.append(candidate)

        for source_root in source_roots:
            for source_path in _pak_files(source_root):
                destination = install_root / content_root / source_path.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                installed_any = True

        if installed_any:
            return install_root
    return None


def _desired_record(server, resolved_id: str) -> dict:
    for entry in ensure_mod_state(server)["desired"]["url"]:
        if entry.get("resolved_id") == resolved_id:
            return entry
    raise ModSupportError(f"Missing QuakeWorld desired-state metadata for '{resolved_id}'")


def _install_url_entry(server, desired_entry: DesiredModEntry) -> InstalledModEntry:
    desired_record = _desired_record(server, desired_entry.resolved_id)
    cache_root = _cache_root(server) / "url"
    cache_root.mkdir(parents=True, exist_ok=True)
    archive_path = cache_root / desired_record["filename"]
    download_to_cache(
        desired_record["download_url"],
        allowed_hosts=(desired_record["allowed_host"],),
        target_path=archive_path,
    )

    content_root = _content_root(server)
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    archive_type = desired_record["archive_type"]
    if archive_type in ("zip", "7z", "tar"):
        _extract_archive(archive_path, stage_root, archive_type)
        install_root = _build_install_stage(stage_root, content_root=content_root)
        if install_root is None:
            raise ModSupportError(
                f"No QuakeWorld pak content was found in the downloaded payload; expected {content_root}/<name>.pak or bare .pak files"
            )
    else:
        stage_single_file(archive_path, stage_root, Path(content_root) / desired_record["filename"])
        install_root = stage_root

    installed_paths = install_staged_tree(
        staged_root=install_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=_allowed_destinations(server),
    )
    return InstalledModEntry(
        source_type=desired_entry.source_type,
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(Path(server.data["dir"]), installed_paths),
    )


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"]).resolve()
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current.exists() and current != server_root:
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
    mods["desired"] = {"url": []}
    mods["installed"] = []
    mods["last_apply"] = "cleanup"
    mods["errors"] = []
    _save_data(server)


def apply_configured_mods(server):
    mods = ensure_mod_state(server)
    if not mods.get("enabled", True):
        return
    _ensure_content_backup(server)
    try:
        reconciled = reconcile_mod_state(
            desired=_desired_entries(server),
            installed=_installed_entries(server),
            install_entry=lambda entry: _install_url_entry(server, entry),
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


def qw_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the QuakeWorld `mod` command desired-state subcommands."""

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
    if action == "add" and source == "url":
        if not identifier:
            raise ServerError("QuakeWorld mod add url requires a pak archive URL or direct pak URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=QW_ALLOWED_MOD_SUFFIXES,
            entry_label="QuakeWorld mod URL entries",
            filename_description="a supported pak or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"QuakeWorld content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("QuakeWorld mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"QuakeWorld content '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported QuakeWorld mod command")


command_functions["mod"] = qw_mod_command


def resolve_download(version=None):
    """Resolve an MVDSV Linux release asset suitable for QuakeWorld."""

    def _matches(asset):
        name = asset.get("name", "").lower()
        return "linux" in name and "amd64" in name

    return resolve_release_asset(MVDSV_LATEST_RELEASE_API, _matches, version=version)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="mvdsv",
):
    """Collect and store configuration values for a QuakeWorld server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "dm2",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["qw"],
        targets=["qw"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27500,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the QuakeWorld server:",
    )
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input("Direct archive URL for the QuakeWorld server: [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "qwserver.tar.gz"
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    _ensure_content_backup(server)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the QuakeWorld server binary."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_binary(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def get_start_command(server):
    """Build the command used to launch a QuakeWorld dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for native Linux Quake-family servers."""

    requirements = {
        "engine": "docker",
        "family": "quake-linux",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for QuakeWorld."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Return the Quake UDP query address used by the qwserver module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the qwserver module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop QuakeWorld using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed QuakeWorld status is not implemented yet."""


def message(server, msg):
    """QuakeWorld has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a QuakeWorld server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported QuakeWorld datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=(
            "url",
            "download_name",
            "exe_name",
            "dir",
            "startmap",
            "hostname",
            "version",
        ),
        backup_module=backup_utils,
    )
