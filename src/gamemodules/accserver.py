"""Assetto Corsa Competizione dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module

import utils.proton as proton
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1430110
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ACC server",
    "The directory to install ACC in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Assetto Corsa Competizione dedicated server to the latest version.",
    "Restart the Assetto Corsa Competizione dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="server/accServer.exe"):
    """Collect and store configuration values for an ACC server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "configdir": "cfg",
            "configfile": "configuration.json",
            "settingsfile": "settings.json",
            "eventfile": "event.json",
            "eventrulesfile": "eventRules.json",
            "connectionfile": "assistRules.json",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["cfg"],
        targets=["cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=9231,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ACC server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the ACC server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the ACC server files and optionally restart the server."

restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the ACC server."


def get_start_command(server):
    """Build the command used to launch an ACC dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cfg = os.path.join(server.data["dir"], server.data["configdir"])
    return (
        [
            "./" + server.data["exe_name"],
            cfg,
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop ACC by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


status = gamemodule_common.make_noop_status_hook()
status.__doc__ = "Detailed ACC status is not implemented yet."


def message(server, msg):
    """ACC has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ACC server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ACC datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=(
            "configdir",
            "configfile",
            "settingsfile",
            "eventfile",
            "eventrulesfile",
            "connectionfile",
            "exe_name",
            "dir",
        ),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
