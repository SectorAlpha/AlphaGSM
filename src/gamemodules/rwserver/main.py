"""Rising World dedicated server lifecycle helpers."""

import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 339010
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Rising World in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Rising World dedicated server to the latest version.",
    "Restart the Rising World dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "servername", "world")


def _sync_derived_ports(server):
    if "port" not in server.data:
        return
    server.data["queryport"] = int(server.data["port"]) - 1


def _config_path(server):
    return os.path.join(server.data["dir"], "server.properties")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="RisingWorldServer.x64",
):
    """Collect and store configuration values for a Rising World server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "world": server.name,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Logs", "world", "plugins", "server.properties"],
        targets=["Logs", "world", "plugins", "server.properties"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=4255,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Rising World server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    _sync_derived_ports(server)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Rising World server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Rising World server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Rising World server."


def sync_server_config(server):
    """Write supported datastore values to Rising World's server.properties."""

    _sync_derived_ports(server)
    rewrite_equals_config(
        _config_path(server),
        {
            "Server_Port": int(server.data["port"]),
            "Server_Name": str(
                server.data.get("servername", "AlphaGSM %s" % (server.name,))
            ),
            "World_Name": str(server.data.get("world", server.name)),
        },
    )


def get_start_command(server):
    """Build the command used to launch a Rising World dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    sync_server_config(server)
    return (
        [
            "sh",
            "-lc",
            (
                'export LD_LIBRARY_PATH="$PWD/linux64:$PWD:${LD_LIBRARY_PATH:-}"; '
                "exec ./" + shlex.quote(server.data["exe_name"])
            ),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return Rising World's HTTP query TCP endpoint."""

    _sync_derived_ports(server)
    return runtime_module.resolve_query_host(server), int(server.data["queryport"]), "tcp"


def get_info_address(server):
    """Return the Rising World TCP info endpoint."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Rising World using the standard console command."""

    runtime_module.send_to_server(server, "\nstop\n")


def status(server, verbose):
    """Detailed Rising World status is not implemented yet."""


def message(server, msg):
    """Rising World has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Rising World server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Rising World datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("servername", "world", "exe_name", "dir"),
        backup_module=backup_utils,
    )


def get_runtime_requirements(server):
    """Return Rising World's native Linux Docker runtime contract."""

    mounts = None
    if "dir" in server.data:
        mounts = [
            {
                "source": server.data["dir"],
                "target": "/srv/server",
                "mode": "rw",
            },
            {
                "source": os.path.normpath(steamcmd.STEAMCMD_DIR),
                "target": CONTAINER_STEAMCMD_DIR,
                "mode": "ro",
            },
        ]

    _sync_derived_ports(server)
    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "queryport", "protocol": "tcp"},
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        mounts=mounts,
    )


def get_container_spec(server):
    """Run the native Linux server in Docker as the mounted server owner."""

    requirements = get_runtime_requirements(server)
    command, _cwd = get_start_command(server)
    shell_command = " ".join(shlex.quote(part) for part in command)
    user_shell_command = "cd /srv/server && " + shell_command
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "tty": False,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            "sh",
            "-lc",
            (
                'id -u alphagsm >/dev/null 2>&1 || useradd -M -u 1000 -o alphagsm; '
                'mkdir -p /home/alphagsm/.steam/sdk64; '
                'chmod -R a+rwX /srv/server /home/alphagsm; '
                'ln -sfn '
                + CONTAINER_STEAMCMD_DIR
                + '/linux64/steamclient.so /home/alphagsm/.steam/sdk64/steamclient.so; '
                'export HOME=/home/alphagsm USER=alphagsm LOGNAME=alphagsm; '
                "exec runuser -u alphagsm -- sh -lc "
                + shlex.quote(user_shell_command)
            ),
        ],
    }
