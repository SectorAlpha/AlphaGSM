"""Chivalry: Medieval Warfare dedicated server lifecycle helpers."""

import os
import errno

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 220070
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Chivalry server",
    "The directory to install Chivalry in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Chivalry dedicated server to the latest version.",
    "Restart the Chivalry dedicated server.",
)
command_functions = {}
config_sync_keys = ("port", "queryport")
max_stop_wait = 1


def _engine_config_path(server):
    """Return the managed Chivalry engine config path."""

    return os.path.join(server.data["dir"], "UDKGame", "Config", "PCServer-UDKEngine.ini")


def sync_server_config(server):
    """Persist managed port values into Chivalry's native engine config."""

    config_path = _engine_config_path(server)
    if not os.path.isfile(config_path):
        return
    replacements = {
        "Port": str(server.data["port"]),
        "PeerPort": str(int(server.data["port"]) + 1),
        "QueryPort": str(server.data["queryport"]),
    }
    with open(config_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    updated_lines = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        replaced = False
        for key_name, value in replacements.items():
            if stripped.startswith(key_name + "="):
                updated_lines.append(f"{key_name}={value}\n")
                seen.add(key_name)
                replaced = True
                break
        if not replaced:
            updated_lines.append(line)
    for key_name, value in replacements.items():
        if key_name not in seen:
            updated_lines.append(f"{key_name}={value}\n")
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.writelines(updated_lines)


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Linux/UDKGameServer-Linux"):
    """Collect and store configuration values for a Chivalry server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "AOCTO-Battlegrounds_V3_P",
            "queryport": 27015,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["UDKGame", "Binaries"],
        targets=["UDKGame", "Binaries"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Chivalry server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Chivalry server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Chivalry server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Chivalry server."


def prestart(server):
    """Sync Chivalry's managed engine config before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Chivalry exposes Steam A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_start_command(server):
    """Build the command used to launch a Chivalry dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    install_dir = os.path.normpath(server.data["dir"])
    exe_dir = os.path.dirname(exe_path)
    lib_dir = os.path.join(exe_dir, "lib")
    loader_alias = os.path.join(lib_dir, "PhysXUpdateLoader.so")
    loader_target = "libPhysXLoader.so.1"
    if not os.path.exists(loader_alias):
        target_path = os.path.join(lib_dir, loader_target)
        if os.path.exists(target_path):
            try:
                os.symlink(loader_target, loader_alias)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
    launch_url = "%s?Port=%s?QueryPort=%s?steamsockets" % (
        server.data["startmap"],
        server.data["port"],
        server.data["queryport"],
    )
    library_path = os.pathsep.join(
        filter(
            None,
            (
                os.path.join(steamcmd.STEAMCMD_DIR, "linux32"),
                install_dir,
                os.path.join(install_dir, "linux64"),
                exe_dir,
                lib_dir,
                os.environ.get("LD_LIBRARY_PATH"),
            ),
        )
    )
    return (
        [
            "env",
            "LD_LIBRARY_PATH=" + library_path,
            "./" + os.path.basename(server.data["exe_name"]),
            launch_url,
            "-Port=%s" % (server.data["port"],),
            "-PeerPort=%s" % (int(server.data["port"]) + 1,),
            "-QueryPort=%s" % (server.data["queryport"],),
            "-SEEKFREELOADINGSERVER",
        ],
        exe_dir,
    )


def do_stop(server, j):
    """Stop Chivalry by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Chivalry status is not implemented yet."""


def message(server, msg):
    """Chivalry has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Chivalry server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Chivalry datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("startmap", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}),
        stdin_open=True,
)
