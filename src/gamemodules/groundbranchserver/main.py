"""GROUND BRANCH dedicated server lifecycle helpers."""

import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 476400
steam_anonymous_login_possible = True
_PORT_DEFINITIONS = (
    {"key": "queryport", "protocol": "udp"},
    {"key": "port", "protocol": "udp"},
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the GROUND BRANCH server",
    "The directory to install GROUND BRANCH in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the GROUND BRANCH dedicated server to the latest version.",
    "Restart the GROUND BRANCH dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "bindaddress": SettingSpec(
        canonical_key="bindaddress",
        description="The IP address used for the game and Steam query listeners.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="MultiHome={value}",
        examples=("0.0.0.0",),
    ),
    **gamemodule_common.build_unreal_setting_schema(
        include_maxplayers=True,
        port_format="Port={value}",
        queryport_format="QueryPort={value}",
        maxplayers_format="?MaxPlayers={value}",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="GroundBranch/Binaries/Win64/GroundBranchServer-Win64-Shipping.exe"):
    """Collect and store configuration values for a GROUND BRANCH server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "bindaddress": "0.0.0.0",
            "queryport": "27015",
            "maxplayers": "16",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["GroundBranch/Saved", "GroundBranch/Config"],
        targets=["GroundBranch/Saved", "GroundBranch/Config"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the GROUND BRANCH server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the GROUND BRANCH server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a GROUND BRANCH dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_data = dict(server.data)
    launch_data.setdefault("bindaddress", "0.0.0.0")
    dynamic_args = build_launch_arg_values(
        launch_data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    # GROUND BRANCH reads player limits from URL options before engine settings.
    dynamic_args.sort(key=lambda argument: not argument.startswith("?"))
    cmd = [
            server.data["exe_name"],
            *dynamic_args,
            "-log",
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop GROUND BRANCH by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed GROUND BRANCH status is not implemented yet."


def message(server, msg):
    """GROUND BRANCH has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a GROUND BRANCH server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported GROUND BRANCH datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("bindaddress", "exe_name", "dir"),
        backup_module=backup_utils,
    )

def get_query_address(server):
    """Query the native Steam UDP listener on the configured query port."""

    return runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Use the native Steam endpoint for server information."""

    return get_query_address(server)


def get_runtime_requirements(server):
    """Declare GROUND BRANCH's UDP game and Steam query listeners."""

    return proton.get_runtime_requirements(server, port_definitions=_PORT_DEFINITIONS)


def get_container_spec(server):
    """Build the Wine/Proton runtime spec with the native UDP listeners."""

    return proton.get_container_spec(
        server, get_start_command, port_definitions=_PORT_DEFINITIONS,
    )
