"""Arma 3 Altis Life dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 233780
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Arma 3 Altis Life in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Arma 3 Altis Life dedicated server to the latest version.",
    "Restart the Arma 3 Altis Life dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="arma3server_x64"):
    """Collect and store configuration values for an Arma 3 Altis Life server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "world": "Altis",
            "mod": "",
            "mission": "Altis_Life.Altis",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["mpmissions", "profiles", "server.cfg"],
        targets=["mpmissions", "profiles", "server.cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=2302,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Arma 3 Altis Life server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an Arma 3 Altis Life dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "-config=%s" % (server.data["configfile"],),
        "-port=%s" % (server.data["port"],),
        "-profiles=%s" % (server.data["profilesdir"],),
        "-name=%s" % (server.name,),
        "-world=%s" % (server.data["world"],),
        "-autoinit",
        "-mission=%s" % (server.data["mission"],),
    ]
    if server.data["mod"]:
        command.append("-mod=%s" % (server.data["mod"],))
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Arma 3 Altis Life by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Arma 3 Altis Life status is not implemented yet."""


def message(server, msg):
    """Arma 3 Altis Life has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Arma 3 Altis Life server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Arma 3 Altis Life datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("configfile", "profilesdir", "world", "mod", "mission", "exe_name", "dir"),
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
