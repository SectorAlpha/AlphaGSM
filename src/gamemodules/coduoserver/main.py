"""Call of Duty: United Offensive dedicated server lifecycle helpers."""

import os
from pathlib import Path
import shutil

import screen
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
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

CODUO_SERVER_URL = "https://0day.icculus.org/cod/coduo-lnxded-1.51-large.tar.bz2"
CODUO_SERVER_NAME = "coduo-lnxded-1.51-large.tar.bz2"
CODUO_MOD_CACHE_DIRNAME = "coduoserver"
CODUO_ALLOWED_MOD_SUFFIXES = {
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

commands = ("mod",)
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Call of Duty: United Offensive in",
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
command_descriptions = {
    "mod": "Manage Call of Duty: United Offensive pk3 content from direct archive URLs or direct pk3 URLs into the active moddir directory."
}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "moddir", "startmap")
_quake_launch_schema = gamemodule_common.build_quake_setting_schema(
    include_fs_game=True,
    game_key="moddir",
    game_description="The active Call of Duty: United Offensive mod directory.",
    fs_game_tokens=("+set", "fs_game"),
    port_tokens=("+set", "net_port"),
    hostname_tokens=("+set", "sv_hostname"),
    hostname_before_port=True,
)
setting_schema = {
    "fs_game": SettingSpec(
        canonical_key="moddir",
        description=_quake_launch_schema["fs_game"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="moddir",
        launch_arg_tokens=_quake_launch_schema["fs_game"].launch_arg_tokens,
        examples=_quake_launch_schema["fs_game"].examples,
    ),
    "hostname": SettingSpec(
        canonical_key="hostname",
        description=_quake_launch_schema["hostname"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="hostname",
        launch_arg_tokens=_quake_launch_schema["hostname"].launch_arg_tokens,
    ),
    "port": _quake_launch_schema["port"],
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=_quake_launch_schema["startmap"].aliases,
        description=_quake_launch_schema["startmap"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="startmap",
        launch_arg_tokens=_quake_launch_schema["startmap"].launch_arg_tokens,
    ),
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def ensure_mod_state(server):
    """Seed the COD: United Offensive mod desired-state shape and return it."""

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


def _moddir(server) -> str:
    return str(server.data.get("moddir") or server.data.get("fs_game") or "uo")


def _ensure_moddir_backup(server):
    moddir = _moddir(server)
    backupfiles = list(server.data.setdefault("backupfiles", ["uo"]))
    if moddir not in backupfiles:
        backupfiles.append(moddir)
        server.data["backupfiles"] = backupfiles

    backup = server.data.setdefault(
        "backup",
        {
            "profiles": {"default": {"targets": ["uo"]}},
            "schedule": [("default", 0, "days")],
        },
    )
    default_profile = backup.setdefault("profiles", {}).setdefault("default", {"targets": ["uo"]})
    targets = list(default_profile.setdefault("targets", ["uo"]))
    if moddir not in targets:
        targets.append(moddir)
        default_profile["targets"] = targets


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / CODUO_MOD_CACHE_DIRNAME


def _allowed_destinations(server) -> tuple[str, ...]:
    return (_moddir(server),)


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


def _build_install_stage(stage_root: Path, *, moddir: str) -> Path | None:
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

        prefixed_root = candidate / moddir
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
                destination = install_root / moddir / source_path.name
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
    raise ModSupportError(f"Missing Call of Duty: United Offensive desired-state metadata for '{resolved_id}'")


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

    moddir = _moddir(server)
    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)

    archive_type = desired_record["archive_type"]
    if archive_type in ("zip", "7z", "tar"):
        _extract_archive(archive_path, stage_root, archive_type)
        install_root = _build_install_stage(stage_root, moddir=moddir)
        if install_root is None:
            raise ModSupportError(
                f"No Call of Duty: United Offensive pk3 content was found in the downloaded payload; expected {moddir}/<name>.pk3 or bare .pk3 files"
            )
    else:
        stage_single_file(archive_path, stage_root, Path(moddir) / desired_record["filename"])
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
    _ensure_moddir_backup(server)
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


def coduo_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the COD: United Offensive `mod` command desired-state subcommands."""

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
            raise ServerError("Call of Duty: United Offensive mod add url requires a pk3 archive URL or direct pk3 URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=CODUO_ALLOWED_MOD_SUFFIXES,
            entry_label="Call of Duty: United Offensive mod URL entries",
            filename_description="a supported pk3 or archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"Call of Duty: United Offensive content '{resolved['requested_id']}' is already present in desired state"
                )
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("Call of Duty: United Offensive mod remove url requires the original content URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"Call of Duty: United Offensive content '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported Call of Duty: United Offensive mod command")


command_functions["mod"] = coduo_mod_command


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="coduoded_lnxded"):
    """Collect and store configuration values for a COD: United Offensive server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "moddir": "uo",
            "startmap": "mp_brecourt",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["uo"],
        targets=["uo"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28960,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Call of Duty: United Offensive server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=CODUO_SERVER_URL,
        default_name=CODUO_SERVER_NAME,
        prompt="Direct archive URL for the Call of Duty: United Offensive server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    _ensure_moddir_backup(server)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the COD: United Offensive server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = CODUO_SERVER_URL
        server.data.setdefault("download_name", CODUO_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def sync_server_config(server):
    """Rewrite the managed COD: United Offensive server.cfg values from datastore state."""

    moddir = str(server.data.get("moddir", "uo"))
    config_dir = os.path.join(server.data["dir"], moddir)
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "server.cfg")
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "hostname": "AlphaGSM %s" % (server.name,),
            "moddir": "uo",
            "startmap": "mp_brecourt",
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
    """Build the command used to launch a COD: United Offensive dedicated server."""

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


def do_stop(server, j):
    """Stop COD: United Offensive using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Report COD: United Offensive server status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


def message(server, msg):
    """COD: United Offensive has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a COD: United Offensive server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported COD: United Offensive datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("url", "download_name", "exe_name", "dir", "moddir", "startmap", "hostname"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
