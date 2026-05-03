"""Warfork dedicated server lifecycle helpers."""

import os
from pathlib import Path
import shutil

import screen
import server.runtime as runtime_module
import utils.steamcmd as steamcmd
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
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1136510
steam_anonymous_login_possible = True
WF_MOD_CACHE_DIRNAME = "wfserver"
WF_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".pk3": "pk3",
    ".tar.gz": "tar",
    ".tbz2": "tar",
    ".tgz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".tar.bz2": "tar",
    ".tar.xz": "tar",
    ".zip": "zip",
}

commands = ("update", "restart", "mod")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Warfork in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "pk3 archive URL or direct pk3 URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Warfork dedicated server to the latest version.",
    "Restart the Warfork dedicated server.",
)
command_descriptions["mod"] = (
    "Manage Warfork pk3 content from direct archive URLs or direct pk3 URLs into the active fs_game directory."
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "hostname")
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "sv_hostname"),
        port_native_config_key="net_port",
        hostname_native_config_key="sv_hostname",
        include_bind_address=True,
        hostname_before_port=True,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def ensure_mod_state(server):
    """Seed the Warfork mod desired-state shape and return it."""

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
    return str(server.data.get("fs_game") or "basewf")


def _ensure_fs_game_backup(server):
    fs_game = _fs_game(server)
    backupfiles = list(server.data.setdefault("backupfiles", ["basewf"]))
    if fs_game not in backupfiles:
        backupfiles.append(fs_game)
        server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": ["basewf"]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault("default", {"targets": ["basewf"]})
    targets = list(default_profile.setdefault("targets", ["basewf"]))
    if fs_game not in targets:
        targets.append(fs_game)
        default_profile["targets"] = targets


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / WF_MOD_CACHE_DIRNAME


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


def _pk3_files(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_file() and path.name.lower().endswith(".pk3")
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
        pk3_sources = _pk3_files(candidate)
        if pk3_sources:
            source_roots.append(candidate)

        for source_root in source_roots:
            for source_path in _pk3_files(source_root):
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
    raise ModSupportError(f"Missing Warfork desired-state metadata for '{resolved_id}'")


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
                f"No Warfork pk3 content was found in the downloaded payload; expected {fs_game}/<name>.pk3 or bare .pk3 files"
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


def wf_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the Warfork `mod` command desired-state subcommands."""

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
            raise ServerError("Warfork mod add url requires a pk3 archive URL or direct pk3 URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=WF_ALLOWED_MOD_SUFFIXES,
            entry_label="Warfork mod URL entries",
            filename_description="a supported pk3 or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Warfork content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("Warfork mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"Warfork content '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported Warfork mod command")


command_functions["mod"] = wf_mod_command


def configure(server, ask, port=None, dir=None, *, exe_name="wf_server.x86_64"):
    """Collect and store configuration values for a Warfork server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "fs_game": "basewf",
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "wfa1",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["basewf"],
        targets=["basewf"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=44400,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Warfork server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    _ensure_fs_game_backup(server)
    return gamemodule_common.finalize_configure(server)


def sync_server_config(server):
    """Write managed Warfork config values into the autoexec file."""

    autoexec_dir = os.path.join(server.data["dir"], "basewf")
    os.makedirs(autoexec_dir, exist_ok=True)
    autoexec_path = os.path.join(autoexec_dir, "dedicated_autoexec.cfg")
    managed_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "port": 44400,
            "hostname": "AlphaGSM %s" % (server.name,),
        },
        require_explicit_key=True,
    )
    port = int(managed_values["net_port"])
    hostname = managed_values["sv_hostname"]
    with open(autoexec_path, "w", encoding="utf-8") as fh:
        fh.write(f'set net_port {port}\n')
        fh.write('set sv_hostname "%s"\n' % (hostname.replace('"', '\\"'),))


def _validate_startmap(server, startmap):
    """Validate a map name against installed map files when available."""

    server_dir = server.data.get("dir")
    fs_game = server.data.get("fs_game", "basewf")
    if not server_dir:
        return startmap

    candidate_dirs = [
        os.path.join(server_dir, fs_game, "maps"),
        os.path.join(server_dir, "basewf", "maps"),
    ]
    existing_map_dirs = [path for path in candidate_dirs if os.path.isdir(path)]
    if not existing_map_dirs:
        return startmap

    available_maps = set()
    for maps_dir in existing_map_dirs:
        for entry in os.listdir(maps_dir):
            if entry.lower().endswith(".bsp"):
                available_maps.add(os.path.splitext(entry)[0])

    if not available_maps or startmap in available_maps:
        return startmap

    sample = ", ".join(sorted(available_maps)[:10])
    raise ServerError(
        "Unsupported map '%s'. Available installed maps include: %s"
        % (startmap, sample)
    )


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Warfork server files via SteamCMD."""

    _base_install(server)
    # SteamCMD ships a basewf/dedicated_autoexec.cfg that hard-codes
    # net_port 44400. Overwrite it with the configured port after install.
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


_base_update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)


def update(server, validate=True, restart=True):
    """Update the Warfork server files and optionally restart the server."""

    _base_update(server, validate=validate, restart=restart)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Warfork server."


def get_start_command(server):
    """Build the command used to launch a Warfork dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        defaults={"bindaddress": "0.0.0.0"},
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for SteamCMD-backed Linux-native servers."""

    requirements = {
        "engine": "docker",
        "family": "steamcmd-linux",
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
    """Return the Docker launch spec for Warfork."""

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
    """Warfork uses the Quake3/QFusion UDP getstatus query on the game port."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake-format address used by the info command."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Warfork using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Warfork status is not implemented yet."""


def message(server, msg):
    """Warfork has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Warfork server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Warfork datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("fs_game", "hostname", "exe_name", "dir"),
        resolved_handlers={
            "startmap": lambda active_server, *values: _validate_startmap(active_server, str(values[0]))
        },
        backup_module=backup_utils,
    )
