"""Unturned dedicated server lifecycle helpers."""

import json
import os
from pathlib import PurePosixPath

import utils.steamcmd as steamcmd
from server import ServerError
from server.modsupport.native_workshop import (
    build_native_workshop_support,
    safe_server_path,
    write_managed_text,
)
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1110390
steam_anonymous_login_possible = True
workshop_app_id = 304930
MAX_WORKSHOP_CONFIG_BYTES = 1024 * 1024

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Unturned in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Unturned dedicated server to the latest version.",
    "Restart the Unturned dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def _instance_path(server):
    """Require one native instance name before resolving any writable path."""
    instance = str(server.data.get("serverid", server.name))
    if not instance or instance in (".", "..") or any(
        character in instance for character in ("/", "\\", "\x00", "\n", "\r")
    ):
        raise ServerError("Unturned serverid must be a single safe instance name")
    return "Servers/" + instance


def _read_workshop_config(path):
    """Validate native configuration before changing any operator-owned fields."""
    try:
        original = None
        if path.exists():
            with path.open("rb") as handle:
                raw = handle.read(MAX_WORKSHOP_CONFIG_BYTES + 1)
            if len(raw) > MAX_WORKSHOP_CONFIG_BYTES:
                raise ValueError("Workshop configuration exceeds size limit")
            original = raw.decode("utf-8")
        config = json.loads(original) if original is not None else {}
        ids = config.get("File_IDs", []) if isinstance(config, dict) else None
        if not isinstance(ids, list) or any(
            isinstance(item, bool) or not str(item).isascii() or not str(item).isdigit()
            or not 0 < int(item) < 2**64 for item in ids
        ):
            raise ValueError("File_IDs must be a list of positive numeric Workshop IDs")
        return config, original
    except (OSError, ValueError) as exc:
        raise ServerError("Invalid Unturned WorkshopDownloadConfig.json: " + str(exc)) from exc


def _publish_workshop_configs(server, updates, originals):
    """Restore earlier instance configs if publishing a later config fails."""
    written = []
    try:
        for relative, text in updates:
            write_managed_text(server, relative, text)
            written.append(relative)
    except (OSError, ServerError) as exc:
        failed = []
        for relative in reversed(written):
            try:
                if originals[relative] is None:
                    safe_server_path(server, relative).unlink(missing_ok=True)
                else:
                    write_managed_text(server, relative, originals[relative])
            except (OSError, ServerError):
                failed.append(relative)
        if failed:
            raise ServerError(f"Unturned config publication failed; restore managed files: {failed}") from exc
        raise


def configure_workshop(server, item_ids):
    """Merge native activation, removing only IDs previously added by AlphaGSM."""
    relative = _instance_path(server) + "/WorkshopDownloadConfig.json"
    mods = server.data["mods"]
    owned = mods.get("unturned_workshop_ids", {})
    paths = list(dict.fromkeys([*owned, relative]))
    updates = []
    originals = {}
    new_owned = {}
    for config_relative in paths:
        parts = PurePosixPath(config_relative).parts
        if len(parts) != 3 or parts[0] != "Servers" or parts[2] != "WorkshopDownloadConfig.json":
            raise ServerError("Invalid Unturned Workshop configuration ownership path")
        path = safe_server_path(server, config_relative)
        desired = item_ids if config_relative == relative else []
        if not path.exists() and not desired:
            continue
        config, originals[config_relative] = _read_workshop_config(path)
        previous = set(owned.get(config_relative, []))
        remaining = [value for value in config.get("File_IDs", []) if str(int(value)) not in previous]
        operator_ids = {str(int(value)) for value in remaining}
        added = list(dict.fromkeys(value for value in desired if value not in operator_ids))
        config["File_IDs"] = remaining + [int(value) for value in added]
        text = json.dumps(config, indent=2) + "\n"
        if len(text.encode("utf-8")) > MAX_WORKSHOP_CONFIG_BYTES:
            raise ServerError("Unturned Workshop configuration exceeds size limit")
        updates.append((config_relative, text))
        if added:
            new_owned[config_relative] = added
    _publish_workshop_configs(server, updates, originals)
    mods["unturned_workshop_ids"] = new_owned
    # These are configuration references, not wholly owned files to delete.
    return [config_relative for config_relative, _text in updates]


_mod_support = build_native_workshop_support(
    game_label="Unturned", workshop_app_id=workshop_app_id, apply_callback=configure_workshop
)
commands += _mod_support.commands
command_args.update(_mod_support.command_args)
command_descriptions.update(_mod_support.command_descriptions)
command_functions.update(_mod_support.command_functions)
ensure_mod_state = _mod_support.ensure_mod_state
apply_configured_mods = _mod_support.apply_configured_mods
cleanup_configured_mods = _mod_support.cleanup_configured_mods


def sync_server_config(server):
    """Write the port to the native instance config without losing other commands."""

    relative = _instance_path(server) + "/Server/Commands.dat"
    commands_dat = safe_server_path(server, relative)
    lines = []
    if os.path.isfile(commands_dat):
        with open(commands_dat, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    lines = [line for line in lines if not line.split() or line.split()[0].lower() != "port"]
    lines.append("Port %s" % server.data.get("port", 27015))
    write_managed_text(server, relative, "\n".join(lines) + "\n")


def prestart(server):
    """Refresh native server commands before launch."""

    sync_server_config(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


def configure(server, ask, port=None, dir=None, *, exe_name="ServerHelper.sh"):
    """Collect and store configuration values for an Unturned server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "serverid": server.name,
            "launchmode": "InternetServer",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Servers", "ServerHelper.sh"],
        targets=["Servers"],
    )

    if port is None:
        port = server.data.get("port", 27015)
    server.data["port"] = int(port)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Unturned server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Unturned server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Unturned server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Unturned server."


def get_start_command(server):
    """Build the command used to launch an Unturned dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "+%s/%s" % (server.data["launchmode"], server.data["serverid"])],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send save and shutdown commands to Unturned."""

    runtime_module.send_to_server(server, "\nsave\nshutdown\n")


def get_query_address(server):
    """Query Unturned on the base port; gameplay uses the following UDP port."""

    return runtime_module.resolve_query_host(server), int(server.data["port"]), "a2s"


def get_info_address(server):
    """Return Unturned's native Steam query endpoint."""

    return get_query_address(server)


def status(server, verbose):
    """Detailed Unturned status is not implemented yet."""


def message(server, msg):
    """Unturned has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Unturned server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Unturned datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("serverid", "launchmode", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'offset': 1, 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'offset': 1, 'protocol': 'udp'}),
        stdin_open=True,
)
