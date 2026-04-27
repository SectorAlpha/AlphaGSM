"""CS:GO-specific lifecycle, configuration, and update helpers."""

import os
import urllib.request
import json
import time
import datetime
import subprocess as sp
from server import ServerError
import screen
import downloader
import utils.updatefs
from utils import updatefs
import random

from utils.fileutils import make_empty_file
from server.settable_keys import build_launch_arg_values, build_native_config_values
from utils.simple_kv_config import rewrite_space_config as updateconfig
from utils.valve_server import (
    VALVE_SERVER_CONFIG_SYNC_KEYS,
    build_valve_server_setting_schema,
    integration_source_server_config,
    source_query_address,
    validate_source_startmap,
    wake_source_server_for_a2s,
)

import utils.steamcmd as steamcmd

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 740
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install the server in",
)

# required still
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Updates the game server to the latest version.",
    "Restarts the game server without killing the process.",
)
command_functions = {}  # will have elements added as the functions are defined

wake_a2s_query = wake_source_server_for_a2s

max_stop_wait = 1
config_sync_keys = VALVE_SERVER_CONFIG_SYNC_KEYS
setting_schema = {
    **build_valve_server_setting_schema(
        game_name="CS:GO Server",
        default_map="de_dust2",
        max_players=16,
        servername_example="AlphaGSM CS:GO Server",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="srcds_run"):
    """
    This function creates the configuration details for the server

    inputs:
        server: the server object
        ask: whether to request details (e.g port) from the user
        dir: the server installation dir
        *: All arguments after this are keyword only arguments
        exe_name: the executable name of the server
    """

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "mapgroup": "mg_active",
            "startmap": "de_dust2",
            "maxplayers": "16",
            "gametype": "0",
            "gamemode": "0",
            "servername": "AlphaGSM CS:GO Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
    )

    # do we have backup data already? if not initialise the dictionary
    if "backup" not in server.data:
        server.data["backup"] = {}
    if "profiles" not in server.data["backup"]:
        server.data["backup"]["profiles"] = {}
    # if no backup profile exists, create a basic one
    if len(server.data["backup"]["profiles"]) == 0:
        # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
        server.data["backup"]["profiles"]["default"] = {"targets": {}}
    if "schedule" not in server.data["backup"]:
        server.data["backup"]["schedule"] = []
    if len(server.data["backup"]["schedule"]) == 0:
        # if default does not exist, create it
        profile = "default"
        if profile not in server.data["backup"]["profiles"]:
            profile = next(iter(server.data["backup"]["profiles"]))
        # set the default to never back up
        server.data["backup"]["schedule"].append((profile, 0, "days"))

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
        prompt="Where would you like to install the tf2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _disable_incompatible_bundled_libgcc(server):
    """Move the bundled libgcc aside so Source uses the host runtime copy."""

    libgcc_path = os.path.join(server.data["dir"], "bin", "libgcc_s.so.1")
    disabled_path = libgcc_path + ".alphagsm-disabled"
    if os.path.isfile(libgcc_path):
        try:
            os.replace(libgcc_path, disabled_path)
        except FileNotFoundError:
            return disabled_path
        print(
            "Disabled bundled libgcc_s.so.1 for CS:GO/CS2 compatibility: "
            + disabled_path
        )
    return disabled_path


def get_start_command(server):
    """Build the command list used to launch the CS:GO dedicated server."""
    # sample start command
    # ./srcds_run -game csgo -console -usercon +game_type 0 +game_mode 0 +mapgroup mg_active +map de_dust2 -maxplayers 30
    exe_name = server.data["exe_name"]
    if not os.path.isfile(server.data["dir"] + exe_name):
        ServerError("Executable file not found")

    if exe_name[:2] != "./":
        exe_name = "./" + exe_name

    _disable_incompatible_bundled_libgcc(server)

    steamcmd_dir = steamcmd.STEAMCMD_DIR
    steam_updatescript = steamcmd.get_autoupdate_script(
        server.name, server.data["dir"], steam_app_id
    )
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )

    return [
        exe_name,
        "-game",
        "csgo",
        "-console",
        "-usercon",
        "+game_type",
        str(server.data["gametype"]),
        "+game_mode",
        str(server.data["gamemode"]),
        "+sv_pure",
        "1",
        "+ip",
        "0.0.0.0",
        "-secured",
        "-timeout 0",
        "-strictportbind",
        *launch_args[:2],
        "+mapgroup",
        str(server.data["mapgroup"]),
        *launch_args[2:],
        "-autoupdate",
        "-steam_dir",
        steamcmd_dir,
        "-steamcmd_script",
        steam_updatescript,
        "+sv_shutdown_timeout_minutes",
        "2",
    ], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running CS:GO server."""
    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Report CS:GO server status information."""
    pass


def get_query_address(server):
    """Return the live CS:GO query endpoint."""

    return source_query_address(server)


def get_info_address(server):
    """Return the live CS:GO info endpoint."""

    return source_query_address(server)


def sync_server_config(server):
    """Rewrite the CS:GO native server.cfg from datastore values."""

    server_cfg = os.path.join(server.data["dir"], "csgo", "cfg", "server.cfg")
    os.makedirs(os.path.dirname(server_cfg), exist_ok=True)
    if not os.path.isfile(server_cfg):
        make_empty_file(server_cfg)

    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "servername": "AlphaGSM CS:GO Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
        value_transform=lambda _spec, value: '"' + str(value).replace('"', '\\"') + '"',
        require_explicit_key=True,
    )
    integration_cfg = integration_source_server_config()
    if integration_cfg:
        merged_config_values = dict(integration_cfg)
        merged_config_values.update(config_values)
        config_values = merged_config_values
    updateconfig(server_cfg, config_values)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    validate=True,
)
install.__doc__ = "Install or prepare the CS:GO server files for this server object."


# technically this command is not needed, but leaving it commented as an example
#  updateconfig(server_cfg,{"hostport":str(server.data["port"])})


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the server by stopping it and then starting it again."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the CS:GO install through SteamCMD and optionally restart it."


def list_setting_values(server, canonical_key):
    """Return installed map names for the CS:GO map setting."""

    if canonical_key != "map":
        return None
    install_dir = server.data.get("dir")
    if not install_dir:
        return []
    maps_dir = os.path.join(install_dir, "csgo", "maps")
    if not os.path.isdir(maps_dir):
        return []
    return sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(maps_dir)
        if filename.endswith(".bsp")
    )


def checkvalue(server, key, *value):
    """Validate supported CS:GO datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_str_keys=("servername", "rconpassword", "serverpassword"),
        raw_int_keys=(),
        raw_str_keys=("gamemode", "gametype", "mapgroup", "dir", "exe_name"),
        resolved_handlers={
            "map": lambda server_obj, raw_value: validate_source_startmap(
                server_obj, "csgo", raw_value
            ),
        },
        raw_handlers={
            "maxplayers": lambda _server_obj, raw_value: str(int(raw_value)),
            "startmap": lambda server_obj, raw_value: validate_source_startmap(
                server_obj, "csgo", raw_value
            ),
        },
    )


# required, must be defined to allow functions listed below which are not in the defaults to be used
command_functions = {
    "update": update,
    "restart": restart,
}  # will have elements added as the functions are defined

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
