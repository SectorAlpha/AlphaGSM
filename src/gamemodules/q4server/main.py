"""Quake 4 dedicated server lifecycle helpers."""

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
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.gamemodules import common as gamemodule_common
from utils.simple_kv_config import rewrite_equals_config

Q4_SERVER_URL = "https://cloud.quake4.net/files/quake4_linux_1.4.2.x86.run"
Q4_SERVER_NAME = "quake4_linux_1.4.2.x86.run"
Q4_MOD_CACHE_DIRNAME = "q4server"
Q4_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".pk4": "pk4",
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
command_args = gamemodule_common.build_setup_download_command_args(
    "The game port for the server to listen on",
    "The directory to install Quake 4 in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "pk4 archive URL or direct pk4 URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = {
    "mod": "Manage Quake 4 pk4 content from direct archive URLs or direct pk4 URLs into the active fs_game directory."
}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "fs_game", "startmap")
setting_schema = {
    **{
        **gamemodule_common.build_quake_setting_schema(
            include_fs_game=True,
            port_tokens=("+set", "net_port"),
            hostname_tokens=("+set", "si_name"),
        ),
        "fs_game": SettingSpec(
            canonical_key="fs_game",
            description="Game directory/mod to load.",
            apply_to=("datastore", "launch_args", "native_config"),
            native_config_key="fs_game",
            launch_arg_tokens=("+set", "fs_game"),
        ),
        "hostname": SettingSpec(
            canonical_key="hostname",
            aliases=("servername",),
            description="The advertised server name.",
            apply_to=("datastore", "launch_args", "native_config"),
            native_config_key="hostname",
            launch_arg_tokens=("+set", "si_name"),
        ),
        "startmap": SettingSpec(
            canonical_key="startmap",
            aliases=("map",),
            description="Map to start on.",
            apply_to=("datastore", "launch_args", "native_config"),
            native_config_key="startmap",
            launch_arg_tokens=("+map",),
        ),
    },
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def ensure_mod_state(server):
    """Seed the Quake 4 mod desired-state shape and return it."""

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


def _fs_game(server) -> str:
    return str(server.data.get("fs_game") or "q4base")


def _ensure_fs_game_backup(server):
    fs_game = _fs_game(server)
    backupfiles = list(server.data.setdefault("backupfiles", ["q4base"]))
    if fs_game not in backupfiles:
        backupfiles.append(fs_game)
        server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": ["q4base"]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault("default", {"targets": ["q4base"]})
    targets = list(default_profile.setdefault("targets", ["q4base"]))
    if fs_game not in targets:
        targets.append(fs_game)
        default_profile["targets"] = targets


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / Q4_MOD_CACHE_DIRNAME


def _allowed_destinations(server) -> tuple[str, ...]:
    return (_fs_game(server),)


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


def _pk4_files(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_file() and path.name.lower().endswith(".pk4")
    ]


def _build_install_stage(stage_root: Path, *, fs_game: str) -> Path | None:
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

        prefixed_root = candidate / fs_game
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        source_roots = []
        if prefixed_root.is_dir():
            source_roots.append(prefixed_root)
        pk4_sources = _pk4_files(candidate)
        if pk4_sources:
            source_roots.append(candidate)

        for source_root in source_roots:
            for source_path in _pk4_files(source_root):
                destination = install_root / fs_game / source_path.name
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
    raise ModSupportError(f"Missing Quake 4 desired-state metadata for '{resolved_id}'")


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

    fs_game = _fs_game(server)
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    archive_type = desired_record["archive_type"]
    if archive_type in ("zip", "7z", "tar"):
        _extract_archive(archive_path, stage_root, archive_type)
        install_root = _build_install_stage(stage_root, fs_game=fs_game)
        if install_root is None:
            raise ModSupportError(
                f"No Quake 4 pk4 content was found in the downloaded payload; expected {fs_game}/<name>.pk4 or bare .pk4 files"
            )
    else:
        stage_single_file(archive_path, stage_root, Path(fs_game) / desired_record["filename"])
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
    _ensure_fs_game_backup(server)
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


def q4_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the Quake 4 `mod` command desired-state subcommands."""

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
            raise ServerError("Quake 4 mod add url requires a pk4 archive URL or direct pk4 URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=Q4_ALLOWED_MOD_SUFFIXES,
            entry_label="Quake 4 mod URL entries",
            filename_description="a supported pk4 or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Quake 4 content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("Quake 4 mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"Quake 4 content '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported Quake 4 mod command")


command_functions["mod"] = q4_mod_command


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="q4ded.x86"):
    """Collect and store configuration values for a Quake 4 server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "fs_game": "q4base",
            "startmap": "q4dm1",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["q4base"],
        targets=["q4base"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28004,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Quake 4 server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=Q4_SERVER_URL,
        default_name=Q4_SERVER_NAME,
        prompt="Direct archive URL for the Quake 4 server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    _ensure_fs_game_backup(server)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the Quake 4 server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = Q4_SERVER_URL
        server.data.setdefault("download_name", Q4_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def sync_server_config(server):
    """Rewrite managed Quake 4 config entries from datastore values."""

    fs_game = server.data.get("fs_game", "q4base")
    config_dir = os.path.join(server.data["dir"], fs_game)
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "server.cfg")
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "hostname": "AlphaGSM %s" % (server.name,),
            "fs_game": "q4base",
            "startmap": "q4dm1",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            '"%s"' % (str(current_value),)
            if spec.canonical_key == "hostname"
            else str(current_value)
        ),
    )
    rewrite_equals_config(config_path, config_values)


def get_start_command(server):
    """Build the command used to launch a Quake 4 dedicated server."""

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
    """Return the Docker launch spec for Quake 4."""

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
    """Return the Quake UDP query address used by the q4server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the q4server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Quake 4 using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Quake 4 status is not implemented yet."""


def message(server, msg):
    """Quake 4 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake 4 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Quake 4 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("url", "download_name", "exe_name", "dir", "fs_game", "hostname", "startmap"),
        backup_module=backup_utils,
    )
