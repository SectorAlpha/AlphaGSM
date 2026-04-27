"""Arma 3 headless client lifecycle helpers."""

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
    "The port for the server to connect to",
    "The directory to install the Arma 3 headless client in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Arma 3 headless client to the latest version.",
    "Restart the Arma 3 headless client.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="arma3server_x64"):
    """Collect and store configuration values for an Arma 3 headless client."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "profilesdir": "profiles",
            "connect": "127.0.0.1",
            "password": "",
            "mod": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["profiles"],
        targets=["profiles"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=2302,
        prompt="Please specify the server port to connect to:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Arma 3 headless client:",
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
    """Build the command used to launch an Arma 3 headless client."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "-client",
        "-connect=%s" % (server.data["connect"],),
        "-port=%s" % (server.data["port"],),
        "-profiles=%s" % (server.data["profilesdir"],),
        "-name=%s" % (server.name,),
    ]
    if server.data["password"]:
        command.append("-password=%s" % (server.data["password"],))
    if server.data["mod"]:
        command.append("-mod=%s" % (server.data["mod"],))
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop the Arma 3 headless client by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Arma 3 headless client status is not implemented yet."""


def message(server, msg):
    """The Arma 3 headless client has no simple generic message support."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Arma 3 headless client."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Arma 3 headless client datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("profilesdir", "connect", "password", "mod", "exe_name", "dir"):
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
