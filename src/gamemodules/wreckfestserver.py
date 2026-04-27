"""Wreckfest dedicated server lifecycle helpers."""

import os
import re

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 361580
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Wreckfest server",
    "The directory to install Wreckfest in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Wreckfest dedicated server to the latest version.",
    "Restart the Wreckfest dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def configure(server, ask, port=None, dir=None, *, exe_name="WreckfestServer"):
    """Collect and store configuration values for a Wreckfest server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"configfile": "server_config.cfg"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["server_config.cfg", "savegame"],
        targets=["server_config.cfg", "savegame"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=33540,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Wreckfest server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def sync_server_config(server):
    """Update server_port in the server config file to match server.data."""
    port = server.data.get("port")
    if port is None:
        return
    config_path = os.path.join(
        server.data["dir"],
        server.data.get("configfile", "server_config.cfg"),
    )
    if not os.path.isfile(config_path):
        return
    with open(config_path, encoding="utf-8") as fh:
        content = fh.read()
    new_content = re.sub(
        r"^(server_port\s*=)\s*\d+",
        r"\g<1>" + str(port),
        content,
        flags=re.MULTILINE,
    )
    if new_content != content:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
_base_install.__doc__ = "Download the Wreckfest server files via SteamCMD."


def install(server):
    """Download the Wreckfest server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Wreckfest server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Wreckfest server."


def get_start_command(server):
    """Build the command used to launch a Wreckfest dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            server.data["configfile"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Wreckfest using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Wreckfest status is not implemented yet."""


def message(server, msg):
    """Wreckfest has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Wreckfest server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Wreckfest datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("configfile", "exe_name", "dir"),
    )

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
