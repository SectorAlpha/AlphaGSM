"""Counter-Strike 2-specific lifecycle, configuration, and update helpers."""

import os

from server import ServerError
from server.settable_keys import build_launch_arg_values, build_native_config_values
from utils.fileutils import make_empty_file
from utils.simple_kv_config import rewrite_space_config as updateconfig
from utils.valve_server import (
    VALVE_SERVER_CONFIG_SYNC_KEYS,
    build_valve_server_setting_schema,
    integration_source_server_config,
    source_query_address,
    validate_source_startmap,
    wake_source_server_for_a2s,
)
import server.runtime as runtime_module
import utils.steamcmd as steamcmd
from utils.gamemodules import common as gamemodule_common

steam_app_id = 730
steam_anonymous_login_possible = True
wake_a2s_query = wake_source_server_for_a2s

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install the server in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Updates the game server to the latest version.",
    "Restarts the game server without killing the process.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = VALVE_SERVER_CONFIG_SYNC_KEYS
setting_schema = {
    **build_valve_server_setting_schema(
        game_name="CS2 Server",
        default_map="de_dust2",
        max_players=16,
        servername_example="AlphaGSM CS2 Server",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="game/cs2.sh"):
    """Create the basic Counter-Strike 2 configuration details."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "de_dust2",
            "maxplayers": "16",
            "servername": "AlphaGSM CS2 Server",
            "rconpassword": "changeme",
            "serverpassword": "",
        },
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
        prompt="Where would you like to install the cs2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the server by stopping it and then starting it again."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the CS2 install through SteamCMD and optionally restart it."


def get_start_command(server):
    """Build the command list used to launch the Counter-Strike 2 server."""

    exe_name = server.data["exe_name"]
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if exe_name[:2] != "./":
        exe_name = "./" + exe_name

    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )

    return [
        exe_name,
        "-dedicated",
        "-console",
        "-usercon",
        *launch_args,
    ], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running CS2 server."""

    runtime_module.send_to_server(server, "\nquit\n")


def get_query_address(server):
    """Return the live CS2 query endpoint."""

    return source_query_address(server)


def get_info_address(server):
    """Return the live CS2 info endpoint."""

    return source_query_address(server)


def sync_server_config(server):
    """Rewrite the CS2 native server.cfg from datastore values."""

    server_cfg = os.path.join(server.data["dir"], "game", "csgo", "cfg", "server.cfg")
    os.makedirs(os.path.dirname(server_cfg), exist_ok=True)
    if not os.path.isfile(server_cfg):
        make_empty_file(server_cfg)

    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "servername": "AlphaGSM CS2 Server",
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


doinstall = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
doinstall.__doc__ = "Download or refresh the Counter-Strike 2 server files."


def install(server):
    """Install or prepare the Counter-Strike 2 server files."""

    doinstall(server)
    sync_server_config(server)


def list_setting_values(server, canonical_key):
    """Return installed map names for the CS2 map setting."""

    if canonical_key != "map":
        return None
    install_dir = server.data.get("dir")
    if not install_dir:
        return []
    maps_dir = os.path.join(install_dir, "game", "csgo", "maps")
    if not os.path.isdir(maps_dir):
        return []
    return sorted(
        os.path.splitext(filename)[0]
        for filename in os.listdir(maps_dir)
        if filename.endswith(".vpk") or filename.endswith(".bsp")
    )


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


def checkvalue(server, key, *value):
    """Validate supported CS2 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_str_keys=("servername", "rconpassword", "serverpassword"),
        raw_int_keys=(),
        raw_str_keys=("dir", "exe_name"),
        resolved_handlers={
            "map": lambda server_obj, raw_value: validate_source_startmap(
                server_obj, "game/csgo", raw_value
            ),
        },
        raw_handlers={
            "maxplayers": lambda _server_obj, raw_value: str(int(raw_value)),
            "startmap": lambda server_obj, raw_value: validate_source_startmap(
                server_obj, "game/csgo", raw_value
            ),
        },
    )


command_functions = {
    "update": update,
    "restart": restart,
}


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        stdin_open=True,
)
