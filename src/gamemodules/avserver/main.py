"""Avorion dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 565060
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Avorion in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Avorion dedicated server to the latest version.",
    "Restart the Avorion dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="server.sh"):
    """Collect and store configuration values for an Avorion server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "galaxy": server.name,
            "seed": "AlphaGSM",
            "servername": "AlphaGSM %s" % (server.name,),
            "administration": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["galaxies", "server.sh"],
        targets=["galaxies"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27000,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", int(server.data["port"]) + 3)
    server.data.setdefault("steamqueryport", int(server.data["port"]) + 20)
    server.data.setdefault("steammasterport", int(server.data["port"]) + 21)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Avorion server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Avorion server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an Avorion dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "--datapath",
        "./galaxies",
        "--galaxy-name",
        server.data["galaxy"],
        "--server-name",
        server.data["servername"],
        "--port",
        str(server.data["port"]),
        "--query-port",
        str(server.data["queryport"]),
        "--steam-query-port",
        str(server.data["steamqueryport"]),
        "--steam-master-port",
        str(server.data["steammasterport"]),
        "--seed",
        server.data["seed"],
    ]
    if server.data.get("administration"):
        command.extend(["--admin", server.data["administration"]])
    return (command, server.data["dir"])


def get_query_address(server):
    """Return the UDP endpoint used for Avorion reachability checks."""

    return (runtime_module.resolve_query_host(server), int(server.data["steamqueryport"]), "udp")


def get_info_address(server):
    """Return the UDP endpoint used for Avorion info output."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Avorion using the standard stop command."""

    screen.send_to_server(server.name, "\nstop\n")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Avorion status is not implemented yet."


def message(server, msg):
    """Avorion has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Avorion server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Avorion datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "steamqueryport", "steammasterport"),
        str_keys=("galaxy", "seed", "administration", "servername", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'steamqueryport', 'protocol': 'udp'}, {'key': 'steamqueryport', 'protocol': 'tcp'}, {'key': 'steammasterport', 'protocol': 'udp'}, {'key': 'steammasterport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'steamqueryport', 'protocol': 'udp'}, {'key': 'steamqueryport', 'protocol': 'tcp'}, {'key': 'steammasterport', 'protocol': 'udp'}, {'key': 'steammasterport', 'protocol': 'tcp'}),
        stdin_open=True,
)
