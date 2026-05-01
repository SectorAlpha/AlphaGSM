"""Rust dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 258550
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Rust server",
    "The directory to install Rust in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Rust dedicated server to the latest version.",
    "Restart the Rust dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="RustDedicated"):
    """Collect and store configuration values for a Rust server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "level": "Procedural Map",
            "worldsize": "3000",
            "maxplayers": "50",
            "seed": "12345",
            "rconport": "28016",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["server", "oxide", "RustDedicated_Data"],
        targets=["server"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28015,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Rust server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Rust server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Rust dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-batchmode",
            "+server.ip",
            "0.0.0.0",
            "+server.port",
            str(server.data["port"]),
            "+server.hostname",
            server.data["hostname"],
            "+server.level",
            server.data["level"],
            "+server.worldsize",
            str(server.data["worldsize"]),
            "+server.maxplayers",
            str(server.data["maxplayers"]),
            "+server.seed",
            str(server.data["seed"]),
            "+rcon.ip",
            "0.0.0.0",
            "+rcon.port",
            str(server.data["rconport"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send the standard quit command to Rust."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Rust status is not implemented yet."


def message(server, msg):
    """Rust has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Rust server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Rust datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "worldsize", "maxplayers", "seed", "rconport"),
        str_keys=("hostname", "level", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'rconport', 'protocol': 'udp'}, {'key': 'rconport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'rconport', 'protocol': 'udp'}, {'key': 'rconport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
