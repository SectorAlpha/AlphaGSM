"""Project CARS dedicated server lifecycle helpers."""

import json
import os

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 332670
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Project CARS server",
    "The directory to install Project CARS in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Project CARS dedicated server to the latest version.",
    "Restart the Project CARS dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "steamport")
port_claim_definitions = ({"key": "steamport", "default": 8766, "protocol": "udp"},)


def _resolve_query_port(server):
    return int(server.data.get("queryport") or (int(server.data["port"]) + 1))


def _write_server_config(path, *, server_name, host_port, query_port, steam_port):
    lines = [
        'logLevel : "info"',
        "name : {}".format(json.dumps("AlphaGSM {}".format(server_name))),
        "secure : true",
        'password : ""',
        "maxPlayerCount : 16",
        'bindIP : ""',
        "steamPort : {}".format(steam_port),
        "hostPort : {}".format(host_port),
        "queryPort : {}".format(query_port),
        "allowEmptyJoin : true",
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def sync_server_config(server):
    """Write the managed Project CARS server.cfg from datastore values."""

    gamemodule_common.set_server_defaults(server, {"steamport": 8766})
    configfile = server.data.get("configfile", "server.cfg")
    config_path = os.path.join(server.data["dir"], configfile)
    os.makedirs(os.path.dirname(config_path) or server.data["dir"], exist_ok=True)

    host_port = int(server.data["port"])
    query_port = _resolve_query_port(server)
    _write_server_config(
        config_path,
        server_name=server.name,
        host_port=host_port,
        query_port=query_port,
        steam_port=int(server.data["steamport"]),
    )

    canonical_config_path = os.path.join(server.data["dir"], "server.cfg")
    if os.path.normpath(canonical_config_path) != os.path.normpath(config_path):
        _write_server_config(
            canonical_config_path,
            server_name=server.name,
            host_port=host_port,
            query_port=query_port,
            steam_port=int(server.data["steamport"]),
        )


def configure(server, ask, port=None, dir=None, *, exe_name="DedicatedServerCmd"):
    """Collect and store configuration values for a Project CARS server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"configfile": "server.cfg", "steamport": 8766})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["server.cfg", "lua"],
        targets=["server.cfg", "lua"],
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
        prompt="Where would you like to install the Project CARS server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Project CARS server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Project CARS server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Project CARS server."


def get_query_address(server):
    """Project CARS exposes A2S on its configured query port."""

    return (runtime_module.resolve_query_host(server), _resolve_query_port(server), "a2s")


def get_info_address(server):
    """Return the A2S endpoint used by the info command."""

    return (runtime_module.resolve_query_host(server), _resolve_query_port(server), "a2s")


def get_start_command(server):
    """Build the command used to launch a Project CARS dedicated server."""

    _exe_path, launcher, working_dir = gamemodule_common.resolve_install_launcher(server)
    return (
        [
            launcher,
        ],
        working_dir,
    )


def do_stop(server, j):
    """Stop Project CARS using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Project CARS status is not implemented yet."""


def message(server, msg):
    """Project CARS has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Project CARS server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Project CARS datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "steamport"),
        str_keys=("configfile", "exe_name", "dir"),
    )

def _port_definitions(server):
    query = {"key": "queryport", "protocol": "udp"}
    if not server.data.get("queryport"):
        query = {"key": "port", "offset": 1, "protocol": "udp"}
    return ({"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
            *port_claim_definitions, query)


def get_runtime_requirements(server):
    """Declare the native game and A2S query ports for both runtimes."""

    return runtime_module.build_runtime_requirements(
        server, family="steamcmd-linux", port_definitions=_port_definitions(server),
    )


def get_container_spec(server):
    """Publish the same query endpoint used by server.cfg and info."""

    return runtime_module.build_container_spec(
        server, family="steamcmd-linux", get_start_command=get_start_command,
        port_definitions=_port_definitions(server), stdin_open=True,
    )
