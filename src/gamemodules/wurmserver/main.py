"""Wurm Unlimited dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 402370
steam_anonymous_login_possible = True

DEFAULT_LAUNCH_CONFIG = """[Runtime]
OverrideDefaultJavaPath=false
JavaPath=
[Memory]
InitialHeap=512m
MaxHeapSize=2048m
[Utility]
CleanLogsOnStart=true
[VMParams]
JvmParam0=-XX:+AggressiveOpts
"""

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Wurm Unlimited in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Wurm Unlimited dedicated server to the latest version.",
    "Restart the Wurm Unlimited dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def _parse_port(value):
    """Parse a Wurm port value constrained to Java's signed short range."""

    port = int(value)
    if not 1 <= port <= 32767:
        raise ServerError("Port must be between 1 and 32767 for Wurm")
    return port


def configure(server, ask, port=None, dir=None, *, exe_name="WurmServerLauncher"):
    """Collect and store configuration values for a Wurm Unlimited server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "worldname": "Adventure",
            "queryport": 27016,
            "internalport": 7220,
            "rmiport": 7221,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Adventure", "Creative", "WurmServerLauncher"],
        targets=["Adventure", "Creative"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=3724,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Wurm Unlimited server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _finalize_install_layout(server):
    """Restore Wurm's expected launcher files and bundled worlds after install."""

    steamclient_src = os.path.join(server.data["dir"], "linux64", "steamclient.so")
    steamclient_dst = os.path.join(server.data["dir"], "nativelibs", "steamclient.so")
    launch_config = os.path.join(server.data["dir"], "LaunchConfig.ini")
    if os.path.isfile(steamclient_src):
        os.makedirs(os.path.dirname(steamclient_dst), exist_ok=True)
        with open(steamclient_src, "rb") as src_file, open(steamclient_dst, "wb") as dst_file:
            dst_file.write(src_file.read())
    if not os.path.isfile(launch_config):
        with open(launch_config, "w", encoding="utf-8") as launch_config_file:
            launch_config_file.write(DEFAULT_LAUNCH_CONFIG)
    for world_name in ("Adventure", "Creative"):
        bundled_world = os.path.join(server.data["dir"], "dist", world_name)
        install_world = os.path.join(server.data["dir"], world_name)
        if os.path.isdir(bundled_world) and not os.path.exists(install_world):
            shutil.copytree(bundled_world, install_world)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Wurm Unlimited server files via SteamCMD."""

    _base_install(server)
    _finalize_install_layout(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Wurm Unlimited server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Wurm Unlimited server."


def get_start_command(server):
    """Build the command used to launch a Wurm Unlimited dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "start=%s" % (server.data["worldname"],),
            "ip=127.0.0.1",
            "externalport=%s" % (server.data["port"],),
            "queryport=%s" % (server.data["queryport"],),
            "rmiregport=%s" % (server.data["internalport"],),
            "rmiport=%s" % (server.data["rmiport"],),
            "servername=%s" % (server.data["servername"],),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the TCP endpoint used for generic Wurm reachability checks."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")


def get_info_address(server):
    """Return the TCP endpoint used for generic Wurm info output."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Wurm Unlimited using the standard shutdown command."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed Wurm Unlimited status is not implemented yet."""


def message(server, msg):
    """Wurm Unlimited has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Wurm Unlimited server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Wurm Unlimited datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        str_keys=("servername", "exe_name", "dir", "worldname"),
        custom_handlers={
            "port": lambda _server, *values: _parse_port(values[0]),
            "queryport": lambda _server, *values: _parse_port(values[0]),
            "internalport": lambda _server, *values: _parse_port(values[0]),
            "rmiport": lambda _server, *values: _parse_port(values[0]),
        },
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'internalport', 'protocol': 'udp'}, {'key': 'internalport', 'protocol': 'tcp'}, {'key': 'rmiport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'internalport', 'protocol': 'udp'}, {'key': 'internalport', 'protocol': 'tcp'}, {'key': 'rmiport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
