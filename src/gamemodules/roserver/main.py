"""Red Orchestra: Ostfront 41-45 dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 223250
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Red Orchestra in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Red Orchestra dedicated server to the latest version.",
    "Restart the Red Orchestra dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="System/ucc-bin"):
    """Collect and store configuration values for a Red Orchestra server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "Ostfront-Rakowice",
            "gametype": "ROEngine.ROTeamGame",
            "configfile": "System/RedOrchestra.ini",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["System", "Maps", "Textures"],
        targets=["System", "Maps", "Textures"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7757,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Red Orchestra server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Red Orchestra server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Red Orchestra server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Red Orchestra server."


def get_start_command(server):
    """Build the command used to launch a Red Orchestra dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "server",
            "%s?Game=%s" % (server.data["startmap"], server.data["gametype"]),
            "-port=%s" % (server.data["port"],),
            "-ini=%s" % (server.data["configfile"],),
            "-log=server.log",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Red Orchestra using the standard exit command."""

    screen.send_to_server(server.name, "\nexit\n")


def status(server, verbose):
    """Detailed Red Orchestra status is not implemented yet."""


def message(server, msg):
    """Red Orchestra has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Red Orchestra server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Red Orchestra datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("startmap", "gametype", "configfile", "exe_name", "dir"),
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
