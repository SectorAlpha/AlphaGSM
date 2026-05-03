"""7 Days to Die dedicated server lifecycle helpers."""

import os
from pathlib import Path
import re
import shutil

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.modsupport.downloads import (
    download_to_cache,
    extract_7z_safe,
    extract_tarball_safe,
    extract_zip_safe,
    install_staged_tree,
)
from server.modsupport.errors import ModSupportError
from server.modsupport.models import DesiredModEntry, InstalledModEntry
from server.modsupport.ownership import build_owned_manifest
from server.modsupport.providers import resolve_direct_url_entry
from server.modsupport.reconcile import reconcile_mod_state
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 294420
steam_anonymous_login_possible = True
SEVENDAY_MOD_CACHE_DIRNAME = "sevendaystodie"
SEVENDAY_ALLOWED_MOD_SUFFIXES = {
    ".7z": "7z",
    ".tar.gz": "tar",
    ".tbz2": "tar",
    ".tgz": "tar",
    ".txz": "tar",
    ".tar": "tar",
    ".tar.bz2": "tar",
    ".tar.xz": "tar",
    ".zip": "zip",
}
SEVENDAY_MOD_DESTINATION = Path("Mods")
SEVENDAY_ALLOWED_MOD_DESTINATIONS = (str(SEVENDAY_MOD_DESTINATION),)

commands = ("update", "restart", "mod")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the 7 Days to Die server",
    "The directory to install 7 Days to Die in",
)
command_args.update(
    {
        "mod": CmdSpec(
            requiredarguments=(ArgSpec("ACTION", "mod action", str),),
            optionalarguments=(
                ArgSpec("SOURCE", "url", str),
                ArgSpec("IDENTIFIER", "modlet archive URL", str),
                ArgSpec("EXTRA", "optional archive filename override", str),
            ),
        )
    }
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the 7 Days to Die dedicated server to the latest version.",
    "Restart the 7 Days to Die dedicated server.",
)
command_descriptions["mod"] = (
    "Manage 7 Days to Die modlet archives from direct URLs into the built-in Mods/ directory."
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "servername", "maxplayers", "serverpassword")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port to use for this server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerPort",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised server name.",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerName",
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum allowed players.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerMaxPlayerCount",
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Optional join password.",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerPassword",
        secret=True,
    ),
}


def ensure_mod_state(server):
    """Seed the 7DTD mod desired-state shape and return it."""

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


def _cache_root(server) -> Path:
    return Path(server.data["dir"]) / ".alphagsm" / "mods" / SEVENDAY_MOD_CACHE_DIRNAME


def _normalize_modlet_name(raw_value: str) -> str:
    normalized = str(raw_value).replace(".", "_").strip()
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", normalized)
    normalized = normalized.strip("_")
    if not normalized:
        raise ModSupportError("7 Days to Die modlet name could not be derived from the upstream archive name")
    return normalized


def _modlet_name_from_filename(filename: str) -> str:
    lower_name = filename.lower()
    for suffix in sorted(SEVENDAY_ALLOWED_MOD_SUFFIXES, key=len, reverse=True):
        if lower_name.endswith(suffix):
            return _normalize_modlet_name(filename[: -len(suffix)])
    return _normalize_modlet_name(Path(filename).stem)


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


def _modlet_dirs(candidate_root: Path) -> list[Path]:
    return [
        path
        for path in sorted(candidate_root.iterdir())
        if path.is_dir() and (path / "ModInfo.xml").is_file()
    ]


def _build_install_stage(stage_root: Path, *, default_modlet_name: str | None = None) -> Path | None:
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

        prefixed_root = candidate / SEVENDAY_MOD_DESTINATION
        install_root = stage_root.parent / f"{stage_root.name}_install"
        if install_root.exists():
            shutil.rmtree(install_root)

        installed_any = False
        if prefixed_root.is_dir():
            for modlet_dir in _modlet_dirs(prefixed_root):
                for source_path in sorted(path for path in modlet_dir.rglob("*") if path.is_file()):
                    relative_path = source_path.relative_to(modlet_dir)
                    destination = install_root / SEVENDAY_MOD_DESTINATION / modlet_dir.name / relative_path
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, destination)
                    installed_any = True
        elif (candidate / "ModInfo.xml").is_file():
            if not default_modlet_name:
                raise ModSupportError(
                    "7 Days to Die archive root contains ModInfo.xml but no modlet name could be derived"
                )
            for source_path in sorted(path for path in candidate.rglob("*") if path.is_file()):
                relative_path = source_path.relative_to(candidate)
                destination = install_root / SEVENDAY_MOD_DESTINATION / default_modlet_name / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination)
                installed_any = True
        else:
            for modlet_dir in _modlet_dirs(candidate):
                for source_path in sorted(path for path in modlet_dir.rglob("*") if path.is_file()):
                    relative_path = source_path.relative_to(modlet_dir)
                    destination = install_root / SEVENDAY_MOD_DESTINATION / modlet_dir.name / relative_path
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
    raise ModSupportError(f"Missing 7 Days to Die desired-state metadata for '{resolved_id}'")


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

    stage_root = cache_root / f"{desired_entry.resolved_id}_stage"
    if stage_root.exists():
        shutil.rmtree(stage_root)
    _extract_archive(archive_path, stage_root, desired_record["archive_type"])

    install_root = _build_install_stage(
        stage_root,
        default_modlet_name=desired_record["modlet_name"],
    )
    if install_root is None:
        raise ModSupportError(
            "No 7 Days to Die modlet content was found in the downloaded payload; expected Mods/<name>/... or a top-level modlet directory containing ModInfo.xml"
        )

    installed_paths = install_staged_tree(
        staged_root=install_root,
        server_root=Path(server.data["dir"]),
        allowed_destinations=SEVENDAY_ALLOWED_MOD_DESTINATIONS,
    )
    return InstalledModEntry(
        source_type=desired_entry.source_type,
        resolved_id=desired_entry.resolved_id,
        installed_files=build_owned_manifest(Path(server.data["dir"]), installed_paths),
    )


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _remove_owned_entry(server, installed_entry: InstalledModEntry) -> None:
    server_root = Path(server.data["dir"]).resolve()
    mod_root = (server_root / SEVENDAY_MOD_DESTINATION).resolve()
    for relative_path in installed_entry.installed_files:
        target = server_root / relative_path
        if target.exists():
            target.unlink()

        current = target.parent
        while current.exists() and current != server_root:
            if not _path_is_within(current, mod_root):
                break
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


def sevenday_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the 7 Days to Die `mod` command desired-state subcommands."""

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
            raise ServerError("7 Days to Die mod add url requires a modlet archive URL")
        resolved = resolve_direct_url_entry(
            identifier,
            filename=extra,
            allowed_suffixes=SEVENDAY_ALLOWED_MOD_SUFFIXES,
            entry_label="7 Days to Die mod URL entries",
            filename_description="a supported modlet archive filename",
        )
        for entry in mods["desired"]["url"]:
            if entry.get("requested_id") == resolved["requested_id"]:
                raise ServerError(
                    f"7 Days to Die modlet '{resolved['requested_id']}' is already present in desired state"
                )
        resolved["modlet_name"] = _modlet_name_from_filename(resolved["filename"])
        mods["desired"]["url"].append(resolved)
        _save_data(server)
        return
    if action == "remove" and source == "url":
        if not identifier:
            raise ServerError("7 Days to Die mod remove url requires the original modlet URL")
        existing = mods["desired"]["url"]
        updated = [entry for entry in existing if entry.get("requested_id") != identifier]
        if len(updated) == len(existing):
            raise ServerError(f"7 Days to Die modlet '{identifier}' is not present in desired state")
        mods["desired"]["url"] = updated
        _save_data(server)
        return
    raise ServerError("Unsupported 7 Days to Die mod command")


command_functions["mod"] = sevenday_mod_command


def configure(server, ask, port=None, dir=None, *, exe_name="startserver.sh"):
    """Collect and store configuration values for a 7 Days to Die server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"configfile": "serverconfig.xml"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saves", "Mods", "serverconfig.xml", "startserver.sh"],
        targets=["Saves", "Mods", "serverconfig.xml"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=26900,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the 7 Days to Die server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


def sync_server_config(server):
    """Update managed serverconfig.xml entries to match server.data."""

    configfile = server.data.get("configfile", "serverconfig.xml")
    config_path = os.path.join(server.data["dir"], configfile)
    if not os.path.isfile(config_path):
        return
    replacements = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "port": 26900,
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": 8,
            "serverpassword": "",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            str(int(current_value)) if spec.value_type == "integer" else str(current_value)
        ),
    )
    if not replacements:
        return
    with open(config_path, encoding="utf-8") as fh:
        content = fh.read()
    new_content = content
    for xml_key, replacement_value in replacements.items():
        new_content = re.sub(
            rf'(<property\s+name="{re.escape(xml_key)}"\s+value=")[^"]*(")',
            r'\g<1>' + replacement_value + r'\2',
            new_content,
        )
    if new_content != content:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the 7 Days to Die server files via SteamCMD."""

    _base_install(server)
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
    """Update the 7 Days to Die server files and optionally restart the server."""

    _base_update(server, validate=validate, restart=restart)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def prestart(server, *args, **kwargs):
    """Refresh serverconfig.xml from the current datastore before launch."""

    sync_server_config(server)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the 7 Days to Die server."


def get_start_command(server):
    """Build the command used to launch a 7 Days to Die dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "-configfile=%s" % (server.data["configfile"],)],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send the standard shutdown command to 7 Days to Die."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed 7 Days to Die status is not implemented yet."""


def message(server, msg):
    """7 Days to Die has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a 7 Days to Die server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported 7 Days to Die datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("configfile", "exe_name", "dir", "servername", "serverpassword"),
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
