"""Beasts of Bermuda dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 882430
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Beasts of Bermuda in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Beasts of Bermuda dedicated server to the latest version.",
    "Restart the Beasts of Bermuda dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="BeastsOfBermudaServer.sh"):
    """Collect and store configuration values for a Beasts of Bermuda server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "7778",
            "servername": "AlphaGSM %s" % (server.name,),
            "worldname": server.name,
            "password": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved"],
        targets=["Saved"],
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
        prompt="Where would you like to install the Beasts of Bermuda server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Beasts of Bermuda server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Beasts of Bermuda server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Beasts of Bermuda server."


def get_start_command(server):
    """Build the command used to launch a Beasts of Bermuda dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "-log",
        "-port",
        str(server.data["port"]),
        "-queryport",
        str(server.data["queryport"]),
        "-servername",
        server.data["servername"],
        "-world",
        server.data["worldname"],
    ]
    if server.data["password"]:
        command.extend(["-password", server.data["password"]])
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Beasts of Bermuda by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Beasts of Bermuda status is not implemented yet."""


def message(server, msg):
    """Beasts of Bermuda has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Beasts of Bermuda server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Beasts of Bermuda datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("servername", "worldname", "password", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
