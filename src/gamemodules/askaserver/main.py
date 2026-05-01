"""ASKA dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3246670
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ASKA server",
    "The directory to install ASKA in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the ASKA dedicated server to the latest version.",
    "Restart the ASKA dedicated server.",
)
command_functions = {}
setting_schema = {
    "password": SettingSpec(
        canonical_key="password",
        description="Password required to join the server.",
        secret=True,
    ),
}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="AskaServer.exe"):
    """Collect and store configuration values for an ASKA server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": server.name,
            "displayname": "AlphaGSM %s" % (server.name,),
            "password": "",
            "maxplayers": "4",
            "queryport": "27016",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["SaveGames", "ServerConfig"],
        targets=["SaveGames", "ServerConfig"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ASKA server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the ASKA server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)


restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an ASKA dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        server.data["exe_name"],
        "-batchmode",
        "-nographics",
        "-logFile",
        "./server.log",
        "-Port",
        str(server.data["port"]),
        "-QueryPort",
        str(server.data["queryport"]),
        "-ServerName",
        server.data["servername"],
        "-DisplayName",
        server.data["displayname"],
        "-MaxPlayers",
        str(server.data["maxplayers"]),
    ]
    if server.data["password"]:
        command.extend(["-Password", server.data["password"]])
    if IS_LINUX:
        command = proton.wrap_command(
            command, wineprefix=server.data.get("wineprefix")
        )
    return (command, server.data["dir"])


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(("port", "udp"), ("queryport", "udp")),
)
get_runtime_requirements.__doc__ = "Return Docker runtime metadata for Wine/Proton-backed servers."


get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(("port", "udp"), ("queryport", "udp")),
)
get_container_spec.__doc__ = "Return the Docker launch spec for ASKA."


def do_stop(server, j):
    """Stop the ASKA server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed ASKA status is not implemented yet."""


def message(server, msg):
    """ASKA has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ASKA server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ASKA datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("servername", "displayname", "password", "exe_name", "dir"),
    )
