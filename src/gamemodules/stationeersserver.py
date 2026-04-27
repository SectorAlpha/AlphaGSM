"""Stationeers dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 600760
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Stationeers server",
    "The directory to install Stationeers in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Stationeers dedicated server to the latest version.",
    "Restart the Stationeers dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="rocketstation_DedicatedServer.x86_64"):
    """Collect and store configuration values for a Stationeers server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "worldname": "Space",
            "savename": server.name,
            "servername": "AlphaGSM %s" % (server.name,),
            "serverpassword": "",
            "updateport": "27015",
            "maxplayers": "10",
            "autosave": "true",
            "saveinterval": "300",
            "upnp": "false",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["saves"],
        targets=["saves"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27500,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Stationeers server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Stationeers server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Stationeers server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Stationeers server."


def get_start_command(server):
    """Build the command used to launch a Stationeers dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "-loadlatest",
        server.data["savename"],
        server.data["worldname"],
        "-settings",
        "ServerName",
        server.data["servername"],
        "StartLocalHost",
        "true",
        "ServerVisible",
        "true",
        "GamePort",
        str(server.data["port"]),
        "UpdatePort",
        str(server.data["updateport"]),
        "AutoSave",
        server.data["autosave"],
        "SaveInterval",
        str(server.data["saveinterval"]),
        "ServerPassword",
        server.data["serverpassword"],
        "ServerMaxPlayers",
        str(server.data["maxplayers"]),
        "UPNPEnabled",
        server.data["upnp"],
        "-batchmode",
        "-nographics",
    ]
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Stationeers using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Stationeers status is not implemented yet."""


def message(server, msg):
    """Stationeers has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Stationeers server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Stationeers datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "updateport", "saveinterval", "maxplayers"),
        str_keys=(
        "worldname",
        "savename",
        "servername",
        "serverpassword",
        "autosave",
        "upnp",
        "exe_name",
        "dir",
    ),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'updateport', 'protocol': 'udp'}, {'key': 'updateport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'updateport', 'protocol': 'udp'}, {'key': 'updateport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
