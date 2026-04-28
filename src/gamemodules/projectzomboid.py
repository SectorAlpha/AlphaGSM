"""Project Zomboid dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 380870
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The default game port to store for this server",
    "The directory to install Project Zomboid in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Project Zomboid dedicated server to the latest version.",
    "Restart the Project Zomboid dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="start-server.sh"):
    """Collect and store configuration values for a Project Zomboid server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": server.name,
            "adminpassword": "alphagsm",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Zomboid", "Server", "start-server.sh"],
        targets=["Zomboid", "Server"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=16261,
        prompt="Please specify the port to use for this server:",
    )
    # Build 41 dedicated servers expose their direct-connection listener on the
    # fixed UDP port configured in SERVERNAME.ini. Without module-managed config
    # files this remains the upstream default 16262.
    server.data.setdefault("queryport", 16262)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Project Zomboid server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Project Zomboid server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Project Zomboid dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-servername",
            str(server.data["servername"]),
            "-adminpassword",
            str(server.data["adminpassword"]),
            "-port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", 16262)), "udp")


def get_info_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return get_query_address(server)


def do_stop(server, j):
    """Send the standard quit command to Project Zomboid."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Project Zomboid status is not implemented yet."


def message(server, msg):
    """Project Zomboid has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Project Zomboid server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Project Zomboid datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("servername", "adminpassword", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
)
