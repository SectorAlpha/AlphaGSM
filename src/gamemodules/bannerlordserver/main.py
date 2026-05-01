"""Mount & Blade II: Bannerlord dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1863440
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Bannerlord server",
    "The directory to install Bannerlord in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Bannerlord dedicated server to the latest version.",
    "Restart the Bannerlord dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Bannerlord.DedicatedServer"):
    """Collect and store configuration values for a Bannerlord server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "7210",
            "game_type": "CustomBattle",
            "scene": "mp_sergeant_battle",
            "maxplayers": "32",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Configs", "Modules"],
        targets=["Configs", "Modules"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7210,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Bannerlord server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Bannerlord server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Bannerlord server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Bannerlord server."


def get_start_command(server):
    """Build the command used to launch a Bannerlord dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "_MODULES_*Native*Multiplayer*SandBoxCore",
            "_MODULES_*Native*SandBoxCore*Sandbox*CustomBattle",
            "_PORT_%s" % (server.data["port"],),
            "_QUERYPORT_%s" % (server.data["queryport"],),
            "_GAMETYPE_%s" % (server.data["game_type"],),
            "_SCENE_%s" % (server.data["scene"],),
            "_MAXCLIENTS_%s" % (server.data["maxplayers"],),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Bannerlord using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Bannerlord status is not implemented yet."""


def message(server, msg):
    """Bannerlord has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Bannerlord server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Bannerlord datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("game_type", "scene", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
