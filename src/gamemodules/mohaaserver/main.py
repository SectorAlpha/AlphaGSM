"""Medal of Honor: Allied Assault dedicated server lifecycle helpers."""

import os

from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_command_args(
    "The port to use for the Medal of Honor: Allied Assault server",
    "The directory containing the Medal of Honor: Allied Assault server files",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="mohaa_lnxded"):
    """Collect and store configuration values for a MOHAA server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "ip": "0.0.0.0",
            "hostname": "AlphaGSM {}".format(server.name),
            "startmap": "dm/mohdm1",
            "configfile": "main/{}.cfg".format(server.name),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["main", "Logs", "mohaa_lnxded"],
        targets=["main", "Logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=12203,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where are the Medal of Honor: Allied Assault server files located:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """MOHAA uses user-provided files; validate that the dedicated binary is staged."""

    os.makedirs(server.data["dir"], exist_ok=True)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "mohaaserver",
            "an owned Medal of Honor: Allied Assault dedicated server install",
            actions=(
                "Copy the MOHAA dedicated server files into <install_dir> so {} exists".format(
                    server.data["exe_name"]
                ),
                "Retry setup once the 32-bit Linux server files are staged locally",
            ),
            docs_slug="mohaaserver",
        )


def get_start_command(server):
    """Build the command used to launch a MOHAA dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "mohaaserver",
            "an owned Medal of Honor: Allied Assault dedicated server install",
            actions=(
                "Copy the MOHAA dedicated server files into <install_dir> so {} exists".format(
                    server.data["exe_name"]
                ),
                "Retry start after the 32-bit Linux server files are present",
            ),
            docs_slug="mohaaserver",
        )
    runtime_dir = "." if server.data.get("runtime") == "docker" else server.data["dir"]
    return (
        [
            "./" + server.data["exe_name"],
            "+set",
            "sv_punkbuster",
            "0",
            "+set",
            "fs_basepath",
            runtime_dir,
            "+set",
            "fs_outputpath",
            os.path.join(runtime_dir, "Logs"),
            "+set",
            "dedicated",
            "2",
            "+set",
            "net_ip",
            server.data.get("ip", "0.0.0.0"),
            "+set",
            "net_port",
            str(server.data["port"]),
            "+map",
            server.data.get("startmap", "dm/mohdm1"),
            "+exec",
            server.data.get("configfile", "main/{}.cfg".format(server.name)),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """MOHAA only exposes a conservative UDP reachability probe here."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Reuse the MOHAA UDP reachability probe for info."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop MOHAA using the standard in-console quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed MOHAA status is not implemented yet."""


def message(server, msg):
    """MOHAA has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a MOHAA server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported MOHAA datastore edits."""

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
