"""Arma 3 dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 233780
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Arma 3 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Arma 3 dedicated server to the latest version.",
    "Restart the Arma 3 dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("servername",)


def sync_server_config(server):
    """Write managed server.cfg values from datastore settings."""

    configfile = server.data.get("configfile", "server.cfg")
    servername = server.data.get("servername", "AlphaGSM %s" % (server.name,))
    config_path = os.path.join(server.data["dir"], configfile)
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write('hostname = "%s";\n' % (servername.replace('"', '\\"'),))


def configure(server, ask, port=None, dir=None, *, exe_name="arma3server_x64"):
    """Collect and store configuration values for an Arma 3 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "servername": "AlphaGSM %s" % (server.name,),
            "world": "empty",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["mpmissions", "profiles", "server.cfg"],
        targets=["mpmissions", "profiles", "server.cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=2302,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Arma 3 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Arma 3 server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Arma 3 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Arma 3 server."


def get_start_command(server):
    """Build the command used to launch an Arma 3 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-config=%s" % (server.data["configfile"],),
            "-port=%s" % (server.data["port"],),
            "-profiles=%s" % (server.data["profilesdir"],),
            "-name=%s" % (server.name,),
            "-world=%s" % (server.data["world"],),
            "-autoinit",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Arma 3 by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Arma 3 status is not implemented yet."""


def message(server, msg):
    """Arma 3 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Arma 3 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Arma 3 datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("configfile", "profilesdir", "servername", "world", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

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
