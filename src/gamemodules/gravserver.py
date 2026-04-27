"""GRAV dedicated server lifecycle helpers using owned game files."""

import os

import screen
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The game port to use for the GRAV server",
    "The directory containing the GRAV server files",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="CAGGameServer-Win32-Shipping"):
    """Collect and store configuration values for a GRAV server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "peerport": "7778",
            "queryport": "27015",
            "maxplayers": "32",
            "servername": server.name,
            "adminpassword": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["CAGGame", "Cloud"],
        targets=["CAGGame", "Cloud"],
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
        prompt="Where are the GRAV server files located:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """GRAV uses user-provided files; ensure the install directory exists."""

    os.makedirs(server.data["dir"], exist_ok=True)


def get_start_command(server):
    """Build the command used to launch a GRAV dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            'brokerstart?NumHomePlanets=1?AdminPassword=%s?PlanetManagerName="defaultmetaverse"?PlanetPortOffset=0?steamsockets?Port=%s?PeerPort=%s?QueryPort=%s?MaxPlayers=%s?CloudDir="CharacterSaveData"?ServerName="%s"?SteamDontAdvertise=0?AllowPVP=1?DoBaseDecay=1'
            % (
                server.data["adminpassword"],
                server.data["port"],
                server.data["peerport"],
                server.data["queryport"],
                server.data["maxplayers"],
                server.data["servername"],
            ),
            "-seekfreeloadingserver",
            "-unattended",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop GRAV by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed GRAV status is not implemented yet."""


def message(server, msg):
    """GRAV has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a GRAV server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported GRAV datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "peerport", "queryport", "maxplayers"),
        str_keys=("exe_name", "dir", "servername", "adminpassword"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'peerport', 'protocol': 'udp'}, {'key': 'peerport', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'peerport', 'protocol': 'udp'}, {'key': 'peerport', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
