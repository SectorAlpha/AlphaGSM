"""Colony Survival dedicated server lifecycle helpers."""

import json
import os

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 748090
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Colony Survival in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Colony Survival dedicated server to the latest version.",
    "Restart the Colony Survival dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "world", "maxplayers", "servername")


def configure(server, ask, port=None, dir=None, *, exe_name="colonyserver.x86_64"):
    """Collect and store configuration values for a Colony Survival server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "world": server.name,
            "maxplayers": "16",
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["savegames", "server.config.json"],
        targets=["savegames", "server.config.json"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27005,
        prompt="Please specify the game port to use for this server:",
    )
    server.data.setdefault("queryport", str(max(int(server.data["port"]) - 1, 1)))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Colony Survival server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _config_path(server):
    return os.path.join(server.data["dir"], "server.config.json")


def _runtime_config_arg(_server):
    return "server.config.json"


def _template_config_path():
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "docs",
            "server-templates",
            "colserver",
            "server.config.json",
        )
    )


def _load_server_config(server):
    config_path = _config_path(server)
    source_path = config_path if os.path.isfile(config_path) else _template_config_path()
    with open(source_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sync_server_config(server):
    """Keep server.config.json aligned with AlphaGSM-managed settings."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return

    payload = _load_server_config(server)
    payload.setdefault("NewOptions", {})
    payload.setdefault("ServerSettings", {})
    payload["NewOptions"]["WorldName"] = str(server.data.get("world") or server.name)
    payload["ServerSettings"]["ServerName"] = str(
        server.data.get("servername") or ("AlphaGSM %s" % (server.name,))
    )
    payload["ServerSettings"]["ServerIP"] = "0.0.0.0"
    payload["ServerSettings"]["ServerGamePort"] = int(server.data.get("port", 27005))
    payload["ServerSettings"]["ServerQueryPort"] = int(server.data.get("queryport", 27004))
    payload["ServerSettings"]["MaxPlayerCount"] = int(server.data.get("maxplayers", 16))
    payload["ServerSettings"]["NetworkType"] = "SteamOnline"

    config_path = _config_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Colony Survival server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Colony Survival server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Colony Survival server."


def prestart(server):
    """Refresh server.config.json before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for Colony Survival."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "udp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for Colony Survival."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Colony Survival dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-batchmode",
            "-nographics",
            "+server.config",
            _runtime_config_arg(server),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Colony Survival by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Colony Survival status is not implemented yet."""


def message(server, msg):
    """Colony Survival has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Colony Survival server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Colony Survival datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("world", "exe_name", "dir", "servername"),
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    stdin_open=True,
)
