"""Barotrauma dedicated server lifecycle helpers."""

import os
from pathlib import Path

import utils.steamcmd as steamcmd

import server.runtime as runtime_module
from server.modsupport.native_workshop import build_native_workshop_support
from .workshop import WORKSHOP_APP_ID, apply_workshop
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from server.modsupport import owned_payloads

steam_app_id = 1026340
steam_anonymous_login_possible = True
workshop_app_id = WORKSHOP_APP_ID
MOD_SUPPORT = build_native_workshop_support(
    game_label="Barotrauma", workshop_app_id=workshop_app_id, apply_callback=apply_workshop,
)

commands = ("update", "restart") + MOD_SUPPORT.commands
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Barotrauma in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Barotrauma dedicated server to the latest version.",
    "Restart the Barotrauma dedicated server.",
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions = dict(MOD_SUPPORT.command_functions)
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="DedicatedServer"):
    """Collect and store configuration values for a Barotrauma server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "gamemode": "Sandbox",
            "maxplayers": "16",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Data", "serversettings.xml", "config_player.xml"],
        targets=["Data", "serversettings.xml", "config_player.xml"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the port to use for this server:",
    )
    # Barotrauma's Steam query port is game port + 1 by default.
    server.data.setdefault("queryport", str(int(server.data["port"]) + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Barotrauma server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    MOD_SUPPORT.ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


def apply_automatic_mods(server):
    """Respect autoapply for setup, update and startup, including disabled cleanup."""
    if MOD_SUPPORT.ensure_mod_state(server)["autoapply"]:
        MOD_SUPPORT.apply_configured_mods(server)


def prestart(server):
    """Revalidate and activate desired native packages immediately before launch."""
    owned_payloads.publish_owned_payloads(
        server, "btserver-console",
        {".alphagsm/btserver_terminal.py": Path(__file__).with_name("terminal_relay.py").read_bytes()},
    )
    apply_automatic_mods(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=apply_automatic_mods,
)
install.__doc__ = "Download the Barotrauma server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=apply_automatic_mods,
)
update.__doc__ = "Update the Barotrauma server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Barotrauma server."


def get_start_command(server):
    """Build the command used to launch a Barotrauma dedicated server."""

    exe_path = gamemodule_common.resolve_install_executable(server)
    working_dir = os.path.dirname(exe_path) or server.data["dir"]
    return (
        [
            "./" + os.path.basename(exe_path),
            "-name",
            server.name,
            "-port",
            str(server.data["port"]),
            "-queryport",
            str(server.data["queryport"]),
            "-gamemode",
            server.data["gamemode"],
        ],
        working_dir,
    )


def do_stop(server, j):
    """Stop Barotrauma using the standard console command."""

    runtime_module.send_to_server(server, "\nexit\n")


def status(server, verbose):
    """Detailed Barotrauma status is not implemented yet."""


def message(server, msg):
    """Barotrauma has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Barotrauma server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_address(server):
    """Return the current Lidgren UDP game-port health surface."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the same UDP health surface used by the info command."""

    return get_query_address(server)


def checkvalue(server, key, *value):
    """Validate supported Barotrauma datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("gamemode", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

def _get_container_start_command(server):
    """Give Barotrauma a terminal behind Docker's portable console FIFO."""
    command, working_dir = get_start_command(server)
    return (["python3", ".alphagsm/btserver_terminal.py", *command], working_dir)


get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=_get_container_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
        tty=True,
        env={"TERM": "xterm"},
)
