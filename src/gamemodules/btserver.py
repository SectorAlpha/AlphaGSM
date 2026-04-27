"""Barotrauma dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1026340
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Barotrauma in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Barotrauma dedicated server to the latest version.",
    "Restart the Barotrauma dedicated server.",
)
command_functions = {}
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
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Barotrauma server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Barotrauma server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Barotrauma server."


def get_start_command(server):
    """Build the command used to launch a Barotrauma dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-name",
            server.name,
            "-port",
            str(server.data["port"]),
            "-queryport",
            str(server.data["queryport"]),
            "-gamemode",
            server.data["gamemode"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Barotrauma using the standard console command."""

    screen.send_to_server(server.name, "\nexit\n")


def status(server, verbose):
    """Detailed Barotrauma status is not implemented yet."""


def message(server, msg):
    """Barotrauma has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Barotrauma server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


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

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
)
