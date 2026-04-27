"""Don't Starve Together dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 343050
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Don't Starve Together in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Don't Starve Together dedicated server to the latest version.",
    "Restart the Don't Starve Together dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="bin64/dontstarve_dedicated_server_nullrenderer_x64"):
    """Collect and store configuration values for a Don't Starve Together server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "cluster": server.name,
            "shard": "Master",
            "confdir": "DoNotStarveTogether",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DoNotStarveTogether"],
        targets=["DoNotStarveTogether"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=10999,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Don't Starve Together server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Don't Starve Together server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Don't Starve Together server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Don't Starve Together server."


def get_start_command(server):
    """Build the command used to launch a DST dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-console",
            "-cluster",
            server.data["cluster"],
            "-shard",
            server.data["shard"],
            "-persistent_storage_root",
            server.data["dir"],
            "-conf_dir",
            server.data["confdir"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop DST using the standard c_shutdown command."""

    screen.send_to_server(server.name, "\nc_shutdown(true)\n")


def status(server, verbose):
    """Detailed DST status is not implemented yet."""


def message(server, msg):
    """DST has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a DST server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported DST datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("cluster", "shard", "confdir", "exe_name", "dir"):
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
