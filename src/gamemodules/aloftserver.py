"""Aloft dedicated server lifecycle helpers using owned game files."""

import os

import screen
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The server port to use for the Aloft server",
    "The directory containing the Aloft server files",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="AloftServerNoGuiLoad.ps1"):
    """Collect and store configuration values for an Aloft server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "mapname": server.name,
            "servername": server.name,
            "visible": "true",
            "privateislands": "false",
            "playercount": "8",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["output.log", "ServerRoomCode.txt", "Saves"],
        targets=["output.log", "ServerRoomCode.txt", "Saves"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=0,
        prompt="Please specify the server port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where are the Aloft server files located:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Aloft uses user-provided files; ensure the install directory exists."""

    os.makedirs(server.data["dir"], exist_ok=True)


def get_start_command(server):
    """Build the command used to launch an Aloft dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "pwsh",
            "./" + server.data["exe_name"],
            "-batchmode",
            "-nographics",
            "-server",
            "load#%s#" % (server.data["mapname"],),
            "servername#%s#" % (server.data["servername"],),
            "log#ERROR#",
            "isvisible#%s#" % (server.data["visible"],),
            "privateislands#%s#" % (server.data["privateislands"],),
            "playercount#%s#" % (server.data["playercount"],),
            "serverport#%s#" % (server.data["port"],),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Aloft by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Aloft status is not implemented yet."""


def message(server, msg):
    """Aloft has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Aloft server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Aloft datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "playercount"),
        str_keys=("exe_name", "dir", "mapname", "servername", "visible", "privateislands"),
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
