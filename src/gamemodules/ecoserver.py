"""Eco dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 739590
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Eco in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Eco dedicated server to the latest version.",
    "Restart the Eco dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="EcoServer"):
    """Collect and store configuration values for an Eco server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "world": server.name,
            "storage": "Storage",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Storage", "Configs"],
        targets=["Storage", "Configs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=3000,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Eco server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Eco server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an Eco dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-nogui",
            "-port",
            str(server.data["port"]),
            "-world",
            server.data["world"],
            "-storedirectory",
            server.data["storage"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Eco using the standard save-and-shutdown command."""

    screen.send_to_server(server.name, "\nsave\nshutdown\n")


def status(server, verbose):
    """Detailed Eco status is not implemented yet."""


def message(server, msg):
    """Eco has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Eco server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Eco datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("world", "storage", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

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
