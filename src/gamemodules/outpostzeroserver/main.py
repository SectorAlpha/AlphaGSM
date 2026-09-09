"""Outpost Zero dedicated server lifecycle helpers."""

import configparser
import os
import shutil

import server.runtime as runtime_module
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import build_launch_arg_values

from utils.platform_info import IS_LINUX
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 762880
steam_anonymous_login_possible = True
DEFAULT_PORT = 7777
DEFAULT_QUERYPORT = 27015
DEFAULT_MAXPLAYERS = 16
DEFAULT_STARTMAP = "RedPlanet"
_CLIENT_STEAM_APP_ID = "677480"
_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "offset": 1, "protocol": "udp"},
    {"key": "queryport", "protocol": "udp"},
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Outpost Zero server",
    "The directory to install Outpost Zero in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Outpost Zero dedicated server to the latest version.",
    "Restart the Outpost Zero dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        positional_key="startmap",
        positional_aliases=("map",),
        include_maxplayers=True,
        include_servername=True,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}
config_sync_keys = ("port", "queryport", "maxplayers", "servername", "startmap")


def configure(server, ask, port=None, dir=None, *, exe_name="WindowsServer/SurvivalGameServer.exe"):
    """Collect and store configuration values for an Outpost Zero server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": str(DEFAULT_QUERYPORT),
            "maxplayers": str(DEFAULT_MAXPLAYERS),
            "servername": "AlphaGSM %s" % (server.name,),
            "startmap": DEFAULT_STARTMAP,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved", "Config"],
        targets=["Saved", "Config"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=DEFAULT_PORT,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Outpost Zero server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _config_dir(server):
    """Return the WindowsServer config directory used by the dedicated server."""

    return os.path.join(
        server.data["dir"],
        "WindowsServer",
        "SurvivalGame",
        "Saved",
        "Config",
        "WindowsServer",
    )


def _game_ini_path(server):
    """Return the managed Game.ini path."""

    return os.path.join(_config_dir(server), "Game.ini")


def _steam_appid_src_path(server):
    """Return the shipped Steam AppID file path."""

    return os.path.join(server.data["dir"], "WindowsServer", "steam_appid.txt")


def _steam_appid_dst_path(server):
    """Return the Steam AppID path expected beside the Win64 binaries."""

    return os.path.join(
        server.data["dir"],
        "WindowsServer",
        "SurvivalGame",
        "Binaries",
        "Win64",
        "steam_appid.txt",
    )


def sync_server_config(server):
    """Write managed Outpost Zero config and Steam bootstrap state."""

    config_dir = _config_dir(server)
    os.makedirs(config_dir, exist_ok=True)

    parser = configparser.ConfigParser()
    parser.optionxform = str
    game_ini_path = _game_ini_path(server)
    if os.path.exists(game_ini_path):
        parser.read(game_ini_path, encoding="utf-8")
    if not parser.has_section("ServerSettings"):
        parser.add_section("ServerSettings")
    parser.set("ServerSettings", "ServerName", str(server.data.get("servername", "")))
    parser.set(
        "ServerSettings",
        "MaxNumberPlayers",
        str(server.data.get("maxplayers", DEFAULT_MAXPLAYERS)),
    )
    with open(game_ini_path, "w", encoding="utf-8") as handle:
        parser.write(handle)

    steam_appid_src = _steam_appid_src_path(server)
    steam_appid_dst = _steam_appid_dst_path(server)
    os.makedirs(os.path.dirname(steam_appid_dst), exist_ok=True)
    if os.path.isfile(steam_appid_src):
        shutil.copyfile(steam_appid_src, steam_appid_dst)
    else:
        with open(steam_appid_dst, "w", encoding="ascii") as handle:
            handle.write(_CLIENT_STEAM_APP_ID + "\n")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Outpost Zero server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def prestart(server):
    """Refresh managed config and Steam bootstrap files before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the effective query address for Outpost Zero."""

    if IS_LINUX:
        return (
            runtime_module.resolve_query_host(server),
            int(server.data["port"]) + 1,
            "udp",
        )
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the effective info address for Outpost Zero."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch an Outpost Zero dedicated server."""

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


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=_PORT_DEFINITIONS,
)
get_runtime_requirements.__doc__ = "Return Docker runtime metadata for Wine/Proton-backed servers."


get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=_PORT_DEFINITIONS,
)
get_container_spec.__doc__ = "Return the Docker launch spec for Outpost Zero."


def do_stop(server, j):
    """Stop Outpost Zero using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Outpost Zero status is not implemented yet."""


def message(server, msg):
    """Outpost Zero has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Outpost Zero server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Outpost Zero datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )
