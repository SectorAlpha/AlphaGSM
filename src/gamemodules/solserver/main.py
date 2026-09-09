"""Soldat dedicated server lifecycle helpers."""

import configparser
import os

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 638500
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Soldat in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Soldat dedicated server to the latest version.",
    "Restart the Soldat dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "maxplayers", "hostname")
_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "port", "offset": 10, "protocol": "tcp"},
)
port_claim_definitions = _PORT_DEFINITIONS
_RUNTIME_EXTRA = {"run_as_host_user": True, "container_home": "/home/alphagsm"}


def configure(server, ask, port=None, dir=None, *, exe_name="soldatserver"):
    """Collect and store configuration values for a Soldat server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "maxplayers": "16",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["configs", "maps", "logs", "soldat.ini"],
        targets=["configs", "maps", "logs", "soldat.ini"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=23073,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Soldat server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _config_path(server):
    for filename in ("soldat.ini", "Soldat.ini", "SOLDAT.INI"):
        path = os.path.join(server.data["dir"], filename)
        if os.path.isfile(path):
            return path
    return os.path.join(server.data["dir"], "soldat.ini")


def sync_server_config(server):
    """Apply classic Soldat settings and enable its native public status file."""

    path = _config_path(server)
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read(path, encoding="utf-8-sig")
    settings = {
        "GAME": {"Logging": "1"},
        "NETWORK": {
            "Port": str(server.data.get("port", 23073)),
            "Max_Players": str(server.data.get("maxplayers", 16)),
            "Server_Name": str(server.data.get("hostname", server.name)),
            "Allow_Download": "1",
        },
    }
    for section, entries in settings.items():
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in entries.items():
            for existing in list(parser[section]):
                if existing.lower() == key.lower():
                    parser.remove_option(section, existing)
            parser.set(section, key, value)
    os.makedirs(server.data["dir"], exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        parser.write(handle, space_around_delimiters=False)


def prestart(server):
    """Refresh the native configuration before launching Soldat."""

    sync_server_config(server)


def get_query_address(server):
    """Read public gamestat status over the native file server on game + 10."""

    return runtime_module.resolve_query_host(server), int(server.data["port"]) + 10, "soldat"


def get_info_address(server):
    """Use the same native Soldat status surface for info."""

    return get_query_address(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Soldat server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Soldat server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Soldat server."


def get_start_command(server):
    """Build the command used to launch a Soldat dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-c",
            os.path.basename(_config_path(server)),
            "-p",
            str(server.data["port"]),
            "-l",
            str(server.data["maxplayers"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Soldat by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Soldat status is not implemented yet."""


def message(server, msg):
    """Soldat has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Soldat server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Soldat datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("hostname", "exe_name", "dir"),
    )

def get_runtime_requirements(server):
    """Run as the host user and claim Soldat's game and file-status ports."""

    return runtime_module.build_runtime_requirements(
        server, family="steamcmd-linux", port_definitions=_PORT_DEFINITIONS,
        extra=_RUNTIME_EXTRA,
    )


def get_container_spec(server):
    """Keep native Soldat away from its root-user early exit in Docker."""

    return runtime_module.build_container_spec(
        server, family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=_PORT_DEFINITIONS, stdin_open=True, extra=_RUNTIME_EXTRA,
    )
