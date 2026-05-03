"""The Front dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2334200
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for The Front server",
    "The directory to install The Front in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update The Front dedicated server to the latest version.",
    "Restart The Front dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        include_maxplayers=True,
        include_servername=True,
        port_format="-port={value}",
    ),
    "servername": SettingSpec(canonical_key="servername", description="The advertised server name."),
    "worldname": SettingSpec(canonical_key="worldname", description="The world name."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="ProjectWar/Binaries/Linux/TheFrontServer",
):
    """Collect and store configuration values for The Front server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "worldname": server.name,
            "maxplayers": "32",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ProjectWar/Saved", "ProjectWar/Config"],
        targets=["ProjectWar/Saved", "ProjectWar/Config"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    server.data.setdefault("queryport", str(int(server.data["port"]) + 2))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install The Front server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download The Front server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_query_address(server):
    """The Front uses Steam A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_start_command(server):
    """Build the command used to launch The Front dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")

    port = int(server.data["port"])
    beacon_port = port + 1
    query_port = int(server.data.get("queryport", port + 2))
    shutdown_service_port = port + 3
    maxplayers = int(server.data.get("maxplayers", 32))
    server_name = str(server.data.get("servername", "AlphaGSM %s" % (server.name,)))

    return (
        [
            "./" + server.data["exe_name"],
            "ProjectWar",
            "ProjectWar_Start?Listen?MaxPlayers=%s" % (maxplayers,),
            "-server",
            "-game",
            "-QueueThreshold=%s" % (maxplayers,),
            "-ServerName=%s" % (server_name,),
            "-log",
            "-locallogtimes",
            "-EnableParallelCharacterMovementTickFunction",
            "-EnableParallelCharacterTickFunction",
            "-UseDynamicPhysicsScene",
            "-port=%s" % (port,),
            "-BeaconPort=%s" % (beacon_port,),
            "-QueryPort=%s" % (query_port,),
            "-Game.PhysicsVehicle=false",
            "-ansimalloc",
            "-Game.MaxFrameRate=35",
            "-ShutDownServicePort=%s" % (shutdown_service_port,),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop The Front using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed The Front status is not implemented yet."""


def message(server, msg):
    """The Front has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for The Front server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported The Front datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("servername", "worldname", "exe_name", "dir"),
        backup_module=backup_utils,
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
