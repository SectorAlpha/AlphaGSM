"""Myth of Empires dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import build_launch_arg_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1794810
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Myth of Empires server",
    "The directory to install Myth of Empires in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Myth of Empires dedicated server to the latest version.",
    "Restart the Myth of Empires dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        include_maxplayers=True,
        include_servername=True,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="MOE/Binaries/Win64/MOEServer.exe"):
    """Collect and store configuration values for a Myth of Empires server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "100",
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["MOE/Saved", "MOE/Config"],
        targets=["MOE/Saved", "MOE/Config"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=12888,
        prompt="Please specify the game port to use for this server:",
    )
    server.data.setdefault("queryport", str(int(server.data["port"]) + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Myth of Empires server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Myth of Empires server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Myth of Empires dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    cmd = [
            server.data["exe_name"],
            "-log",
            *dynamic_args,
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Myth of Empires using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Myth of Empires status is not implemented yet."""


def message(server, msg):
    """Myth of Empires has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Myth of Empires server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_address(server):
    """Return A2S query address for Myth of Empires (queryport, not game port)."""
    return "127.0.0.1", int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Return A2S info address for Myth of Empires (same as query address)."""
    return "127.0.0.1", int(server.data["queryport"]), "a2s"


def checkvalue(server, key, *value):
    """Validate supported Myth of Empires datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)
