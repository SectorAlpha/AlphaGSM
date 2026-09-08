"""Unturned dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1110390
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Unturned in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Unturned dedicated server to the latest version.",
    "Restart the Unturned dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def sync_server_config(server):
    """Write the port to the native instance config without losing other commands."""

    server_dir = os.path.join(
        server.data["dir"], "Servers", server.data.get("serverid", server.name), "Server"
    )
    os.makedirs(server_dir, exist_ok=True)
    commands_dat = os.path.join(server_dir, "Commands.dat")
    lines = []
    if os.path.isfile(commands_dat):
        with open(commands_dat, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    lines = [line for line in lines if not line.split() or line.split()[0].lower() != "port"]
    lines.append("Port %s" % server.data.get("port", 27015))
    with open(commands_dat, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def prestart(server):
    """Refresh native server commands before launch."""

    sync_server_config(server)


def configure(server, ask, port=None, dir=None, *, exe_name="ServerHelper.sh"):
    """Collect and store configuration values for an Unturned server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "serverid": server.name,
            "launchmode": "InternetServer",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Servers", "ServerHelper.sh"],
        targets=["Servers"],
    )

    if port is None:
        port = server.data.get("port", 27015)
    server.data["port"] = int(port)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Unturned server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Unturned server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Unturned server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Unturned server."


def get_start_command(server):
    """Build the command used to launch an Unturned dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "+%s/%s" % (server.data["launchmode"], server.data["serverid"])],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send save and shutdown commands to Unturned."""

    runtime_module.send_to_server(server, "\nsave\nshutdown\n")


def get_query_address(server):
    """Query Unturned on the base port; gameplay uses the following UDP port."""

    return runtime_module.resolve_query_host(server), int(server.data["port"]), "a2s"


def get_info_address(server):
    """Return Unturned's native Steam query endpoint."""

    return get_query_address(server)


def status(server, verbose):
    """Detailed Unturned status is not implemented yet."""


def message(server, msg):
    """Unturned has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Unturned server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Unturned datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("serverid", "launchmode", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'offset': 1, 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'offset': 1, 'protocol': 'udp'}),
        stdin_open=True,
)
