"""Reign Of Kings dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 381690
steam_anonymous_login_possible = False

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Reign Of Kings server",
    "The directory to install Reign Of Kings in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Reign Of Kings dedicated server to the latest version.",
    "Restart the Reign Of Kings dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Server.exe"):
    """Collect and store configuration values for a Reign Of Kings server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "maxplayers": "40",
            "worldname": server.name,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saves", "Config"],
        targets=["Saves", "Config"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=25147,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Reign Of Kings server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Reign Of Kings server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Reign Of Kings dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
            server.data["exe_name"],
            "-port",
            str(server.data["port"]),
            "-queryport",
            str(server.data["queryport"]),
            "-maxplayers",
            str(server.data["maxplayers"]),
            "-worldname",
            str(server.data["worldname"]),
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
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
get_container_spec.__doc__ = "Return the Docker launch spec for Reign Of Kings."


def do_stop(server, j):
    """Stop Reign Of Kings using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Report Reign Of Kings status via shared query/info helpers."


def message(server, msg):
    """Reign Of Kings has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Reign Of Kings server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Reign Of Kings datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("worldname", "exe_name", "dir"),
    )
