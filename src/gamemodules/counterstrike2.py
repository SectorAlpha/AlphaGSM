"""Counter-Strike 2-specific lifecycle, configuration, and update helpers."""

import os

from server import ServerError
from server.settable_keys import build_launch_arg_values, build_native_config_values
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
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
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The Directory to install minecraft in", str),
        )
    ),
    **gamemodule_common.build_update_restart_command_args(),
}
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

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data["startmap"] = "de_dust2"
    server.data["maxplayers"] = "16"
    server.data.setdefault("servername", "AlphaGSM CS2 Server")
    server.data.setdefault("rconpassword", "changeme")
    server.data.setdefault("serverpassword", "")

    if port is None:
        port = server.data.get("port", 27015)
    if ask:
        while True:
            inp = input(
                "Please specify the port to use for this server: "
                + ("(current=" + str(port) + ") " if port is not None else "")
            ).strip()
            if port is not None and inp == "":
                break
            try:
                port = int(inp)
            except ValueError:
                print(inp + " isn't a valid port number")
                continue
            break
    if port is None:
        raise ValueError("No Port")
    server.data["port"] = port

    if dir is None:
        if "dir" in server.data and server.data["dir"] is not None:
            dir = server.data["dir"]
        else:
            dir = os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the cs2 server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = os.path.join(dir, "")

    if "exe_name" not in server.data:
        server.data["exe_name"] = exe_name
    server.data.save()
    return (), {}


def doinstall(server):
    """Install the Counter-Strike 2 server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])

    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def install(server):
    """Install or prepare the Counter-Strike 2 server files."""

    doinstall(server)
    sync_server_config(server)


def restart(server):
    """Restart the server by stopping it and then starting it again."""

    server.stop()
    server.start()


def update(server, validate=False, restart=False):
    """Update the CS2 install through SteamCMD and optionally restart it."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        validate=validate,
    )
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


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
    """Report CS2 server status information."""

    pass


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
