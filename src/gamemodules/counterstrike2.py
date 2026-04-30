"""Counter-Strike 2-specific lifecycle, configuration, and update helpers."""

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
from server.modsupport.providers import (
    GAMEBANANA_ALLOWED_HOSTS,
    resolve_gamebanana_mod,
    validate_workshop_id,
)
from server.modsupport.reconcile import reconcile_mod_state
from server.settable_keys import build_launch_arg_values, build_native_config_values
from utils.fileutils import make_empty_file
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.simple_kv_config import rewrite_space_config as updateconfig
from utils.valve_server import (
    VALVE_SERVER_CONFIG_SYNC_KEYS,
    build_valve_server_setting_schema,
    integration_source_server_config,
    source_query_address,
    validate_source_startmap,
    wake_source_server_for_a2s,
)
import server.runtime as runtime_module
import utils.steamcmd as steamcmd
from utils.gamemodules import common as gamemodule_common

steam_app_id = 730
steam_anonymous_login_possible = True
wake_a2s_query = wake_source_server_for_a2s
CS2_WORKSHOP_APP_ID = 730
ALLOWED_CS2_MOD_DESTINATIONS = ("addons", "cfg")

commands = ("update", "restart", "mod")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install the server in",
)
command_args["mod"] = CmdSpec(
    requiredarguments=(ArgSpec("ACTION", "mod action", str),),
    optionalarguments=(
        ArgSpec("SOURCE", "gamebanana or workshop", str),
        ArgSpec("IDENTIFIER", "provider item id", str),
        ArgSpec("EXTRA", "reserved", str),
    ),
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Updates the game server to the latest version.",
    "Restarts the game server without killing the process.",
)
command_descriptions["mod"] = "Manage CS2 server-side mods from external GameBanana or workshop ids."
command_functions = {}
max_stop_wait = 1
config_sync_keys = VALVE_SERVER_CONFIG_SYNC_KEYS
setting_schema = {
    **build_valve_server_setting_schema(
        game_name="CS2 Server",
        default_map="de_dust2",
        max_players=16,
        servername_example="AlphaGSM CS2 Server",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def ensure_mod_state(server):
    """Seed the CS2 mod datastore shape and return it."""

    mods = server.data.setdefault("mods", {})
    mods.setdefault("enabled", True)
    mods.setdefault("autoapply", True)
    desired = mods.setdefault("desired", {})
    desired.setdefault("gamebanana", [])
    desired.setdefault("workshop", [])
    mods.setdefault("installed", [])
    mods.setdefault("last_apply", None)
    mods.setdefault("errors", [])
    return mods


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
            source_type="gamebanana",
            requested_id=entry["requested_id"],
            resolved_id=entry.get("resolved_id"),
        )
        for entry in mods["desired"]["gamebanana"]
    ]
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


def _payload_has_allowed_content(stage_root: Path) -> bool:
    for path in stage_root.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(stage_root)
        if relative_path.parts and relative_path.parts[0] in set(ALLOWED_CS2_MOD_DESTINATIONS):
            return True
    return False


def _discover_payload_root(stage_root: Path) -> Path:
    stage_root = Path(stage_root)
    candidates = [
        stage_root,
        stage_root / "game" / "csgo",
        stage_root / "csgo",
    ]
    if stage_root.exists():
        top_level_dirs = [path for path in stage_root.iterdir() if path.is_dir()]
        if len(top_level_dirs) == 1:
            candidates.extend(
                [
                    top_level_dirs[0],
                    top_level_dirs[0] / "game" / "csgo",
                    top_level_dirs[0] / "csgo",
                ]
            )

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


def _install_staged_payload(server, stage_root: Path) -> list[str]:
    payload_root = _discover_payload_root(stage_root)
    if not _payload_has_allowed_content(payload_root):
        raise ModSupportError("No CS2 server-side mod content was found in the downloaded payload")

    server_root = Path(server.data["dir"])
    installed_paths = install_staged_tree(
        staged_root=payload_root,
        server_root=server_root / "game" / "csgo",
        allowed_destinations=ALLOWED_CS2_MOD_DESTINATIONS,
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
            CS2_WORKSHOP_APP_ID,
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
    if desired_entry.source_type == "gamebanana":
        return _install_gamebanana_entry(server, desired_entry)
    if desired_entry.source_type == "workshop":
        return _install_workshop_entry(server, desired_entry)
    raise ModSupportError(f"Unsupported CS2 mod source: {desired_entry.source_type}")


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
    """Remove installed CS2 mod files and reset desired-state tracking."""

    mods = ensure_mod_state(server)
    for installed_entry in _installed_entries(server):
        _remove_owned_entry(server, installed_entry)
    shutil.rmtree(_cache_root(server), ignore_errors=True)
    mods["desired"] = {"gamebanana": [], "workshop": []}
    mods["installed"] = []
    mods["last_apply"] = "cleanup"
    mods["errors"] = []
    server.data.save()


def apply_configured_mods(server):
    """Reconcile the configured CS2 mods into the server install."""

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


def cs2_mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Handle the CS2 ``mod`` command desired-state subcommands."""

    del extra, kwargs
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
    if action == "add" and source == "gamebanana":
        if not identifier:
            raise ServerError("CS2 mod add gamebanana requires a numeric GameBanana item id")
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
    raise ServerError("Unsupported CS2 mod command")


def configure(server, ask, port=None, dir=None, *, exe_name="game/cs2.sh"):
    """Create the basic Counter-Strike 2 configuration details."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "de_dust2",
            "maxplayers": "16",
            "servername": "AlphaGSM CS2 Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the cs2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the server by stopping it and then starting it again."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the CS2 install through SteamCMD and optionally restart it."


def get_start_command(server):
    """Build the command list used to launch the Counter-Strike 2 server."""

    exe_name = server.data["exe_name"]
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if exe_name[:2] != "./":
        exe_name = "./" + exe_name

    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )

    return [
        exe_name,
        "-dedicated",
        "-console",
        "-usercon",
        *launch_args,
    ], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running CS2 server."""

    runtime_module.send_to_server(server, "\nquit\n")


def get_query_address(server):
    """Return the live CS2 query endpoint."""

    return source_query_address(server)


def get_info_address(server):
    """Return the live CS2 info endpoint."""

    return source_query_address(server)


def sync_server_config(server):
    """Rewrite the CS2 native server.cfg from datastore values."""

    server_cfg = os.path.join(server.data["dir"], "game", "csgo", "cfg", "server.cfg")
    os.makedirs(os.path.dirname(server_cfg), exist_ok=True)
    if not os.path.isfile(server_cfg):
        make_empty_file(server_cfg)

    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "servername": "AlphaGSM CS2 Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
        value_transform=lambda _spec, value: '"' + str(value).replace('"', '\\"') + '"',
        require_explicit_key=True,
    )
    integration_cfg = integration_source_server_config()
    if integration_cfg:
        merged_config_values = dict(integration_cfg)
        merged_config_values.update(config_values)
        config_values = merged_config_values
    updateconfig(server_cfg, config_values)


doinstall = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
doinstall.__doc__ = "Download or refresh the Counter-Strike 2 server files."


def install(server):
    """Install or prepare the Counter-Strike 2 server files."""

    doinstall(server)
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def list_setting_values(server, canonical_key):
    """Return installed map names for the CS2 map setting."""

    if canonical_key != "map":
        return None
    install_dir = server.data.get("dir")
    if not install_dir:
        return []
    maps_dir = os.path.join(install_dir, "game", "csgo", "maps")
    if not os.path.isdir(maps_dir):
        return []
    return sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(maps_dir)
        if filename.endswith(".vpk") or filename.endswith(".bsp")
    )


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


def checkvalue(server, key, *value):
    """Validate supported CS2 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_str_keys=("servername", "rconpassword", "serverpassword"),
        raw_int_keys=(),
        raw_str_keys=("dir", "exe_name"),
        resolved_handlers={
            "map": lambda server_obj, raw_value: validate_source_startmap(
                server_obj, "game/csgo", raw_value
            ),
        },
        raw_handlers={
            "maxplayers": lambda _server_obj, raw_value: str(int(raw_value)),
            "startmap": lambda server_obj, raw_value: validate_source_startmap(
                server_obj, "game/csgo", raw_value
            ),
        },
    )


command_functions = {
    "mod": cs2_mod_command,
    "update": update,
    "restart": restart,
}


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        stdin_open=True,
)
