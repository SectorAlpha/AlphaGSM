"""Staxel dedicated server lifecycle helpers."""

import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 755170
steam_anonymous_login_possible = False

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Staxel server",
    "The directory to install Staxel in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Staxel dedicated server to the latest version.",
    "Restart the Staxel dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="bin/Staxel.ServerWizard.exe"):
    """Collect and store configuration values for a Staxel server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["data", "mods", "saves"],
        targets=["data", "mods", "saves"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=25565,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Staxel server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Staxel server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Staxel server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Staxel server."


def get_start_command(server):
    """Build the command used to launch a Staxel dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
            server.data["exe_name"],
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Staxel by interrupting the foreground server process."""

    raise ServerError("Automatic stop is not implemented for this server")


def status(server, verbose):
    """Detailed Staxel status is not implemented yet."""


def message(server, msg):
    """Staxel has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Staxel server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Staxel datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
