"""Nightingale dedicated server lifecycle helpers."""

import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3796810
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Nightingale server",
    "The directory to install Nightingale in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Nightingale dedicated server to the latest version.",
    "Restart the Nightingale dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="NWXServer.sh"):
    """Collect and store configuration values for a Nightingale server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"savegame": server.name})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved"],
        targets=["Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.sync_derived_port(server, "queryport", offset=1)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Nightingale server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Nightingale server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Nightingale server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Nightingale server."


def get_start_command(server):
    """Build the command used to launch a Nightingale dedicated server."""

    gamemodule_common.sync_derived_port(server, "queryport", offset=1)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-port={}".format(server.data["port"]),
            "-statusPort={}".format(server.data["queryport"]),
            (
                "-ini:Engine:[HTTPServer.Listeners]:"
                "+ListenerOverrides=(Port={},BindAddress=0.0.0.0)"
            ).format(server.data["queryport"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Nightingale using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Nightingale status is not implemented yet."""


def message(server, msg):
    """Nightingale has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Nightingale server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_address(server):
    """Return the official Nightingale HTTP status endpoint."""

    gamemodule_common.sync_derived_port(server, "queryport", offset=1)
    return (
        runtime_module.resolve_query_host(server),
        int(server.data["queryport"]),
        "http_status",
    )


def get_info_address(server):
    """Return the Nightingale info endpoint."""

    return get_query_address(server)


def checkvalue(server, key, *value):
    """Validate supported Nightingale datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("savegame", "exe_name", "dir"),
        backup_module=backup_utils,
    )

def get_runtime_requirements(server):
    """Return Nightingale's native Linux Docker runtime contract."""

    gamemodule_common.sync_derived_port(server, "queryport", offset=1)
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

    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "queryport", "protocol": "tcp"},
        ),
        mounts=mounts,
    )


def get_container_spec(server):
    """Run the Linux server in Docker as the mounted server-directory owner."""

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
