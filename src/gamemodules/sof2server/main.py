"""Soldier of Fortune 2: Double Helix Gold dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The port to use for the Soldier of Fortune 2 server",
    "The directory containing the Soldier of Fortune 2 server files",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="sof2ded"):
    """Collect and store configuration values for a SOF2 server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "ip": "0.0.0.0",
            "hostname": "AlphaGSM {}".format(server.name),
            "startmap": "mp_shop",
            "configfile": "base/{}.cfg".format(server.name),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["base", "Logs", "sof2ded"],
        targets=["base", "Logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=20100,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where are the Soldier of Fortune 2 server files located:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """SOF2 uses user-provided files; validate that the dedicated binary is staged."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "sof2server",
            "an owned Soldier of Fortune 2 dedicated server install",
            actions=(
                "Copy the SOF2 dedicated server files into <install_dir> so {} exists".format(
                    server.data["exe_name"]
                ),
                "Retry setup once the 32-bit Linux server files are staged locally",
            ),
            docs_slug="sof2server",
        )


def get_start_command(server):
    """Build the command used to launch a SOF2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "sof2server",
            "an owned Soldier of Fortune 2 dedicated server install",
            actions=(
                "Copy the SOF2 dedicated server files into <install_dir> so {} exists".format(
                    server.data["exe_name"]
                ),
                "Retry start after the 32-bit Linux server files are present",
            ),
            docs_slug="sof2server",
        )
    return (
        [
            "./" + server.data["exe_name"],
            "+set",
            "sv_punkbuster",
            "0",
            "+set",
            "dedicated",
            "2",
            "+set",
            "net_ip",
            server.data.get("ip", "0.0.0.0"),
            "+set",
            "net_port",
            str(server.data["port"]),
            "+exec",
            server.data.get("configfile", "base/{}.cfg".format(server.name)),
            "+map",
            server.data.get("startmap", "mp_shop"),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """SOF2 uses the Quake-family UDP getstatus query on the game port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the SOF2 Quake info address."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop SOF2 using the standard in-console quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed SOF2 status is not implemented yet."""


def message(server, msg):
    """SOF2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a SOF2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported SOF2 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("exe_name", "dir", "ip", "hostname", "startmap", "configfile"),
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="quake-linux",
    port_definitions=({"key": "port", "protocol": "udp"},),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
    family="quake-linux",
    get_start_command=get_start_command,
    port_definitions=({"key": "port", "protocol": "udp"},),
    stdin_open=True,
)
