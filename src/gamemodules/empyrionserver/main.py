"""Empyrion - Galactic Survival dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 530870
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Empyrion server",
    "The directory to install Empyrion in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Empyrion dedicated server to the latest version.",
    "Restart the Empyrion dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="DedicatedServer/EmpyrionDedicated.exe"):
    """Collect and store configuration values for an Empyrion server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"queryport": "30004"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saves", "Content", "dedicated.yaml"],
        targets=["Saves", "Content", "dedicated.yaml"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=30000,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Empyrion server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Empyrion server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Empyrion server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Empyrion server."


def get_start_command(server):
    """Build the command used to launch an Empyrion server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"]]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(("port", "udp"), ("queryport", "udp")),
)
get_runtime_requirements.__doc__ = "Return Docker runtime metadata for Wine/Proton-backed servers."


get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(("port", "udp"), ("queryport", "udp")),
)
get_container_spec.__doc__ = "Return the Docker launch spec for Empyrion."


def do_stop(server, j):
    """Stop Empyrion using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Empyrion status is not implemented yet."""


def message(server, msg):
    """Empyrion has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Empyrion server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Empyrion datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("exe_name", "dir"),
    )
