"""Operation: Harsh Doorstop dedicated server lifecycle helpers."""

import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 950900
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Operation: Harsh Doorstop in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Operation: Harsh Doorstop dedicated server to the latest version.",
    "Restart the Operation: Harsh Doorstop dedicated server.",
)
command_functions = {}
max_stop_wait = 1
DEFAULT_EXECUTABLES = (
    "HarshDoorstopServer.sh",
    os.path.join(
        "HarshDoorstop",
        "Binaries",
        "Linux",
        "HarshDoorstopServer-Linux-Shipping",
    ),
)
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        include_servername=True,
        servername_format="-SteamServerName={value}",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="HarshDoorstopServer.sh"):
    """Collect and store configuration values for an OHD server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": "16",
            "map": "AAS-TestMap",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved/Config", "Saved/Logs"],
        targets=["Saved/Config", "Saved/Logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Operation: Harsh Doorstop server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _resolve_executable_name(server):
    """Return the real Harsh Doorstop launcher from the installed Linux payload."""

    configured = server.data.get("exe_name")
    candidates = []
    if configured:
        candidates.append(configured)
    candidates.extend(name for name in DEFAULT_EXECUTABLES if name not in candidates)

    for candidate in candidates:
        if os.path.isfile(os.path.join(server.data["dir"], candidate)):
            return candidate
    raise ServerError("Executable file not found")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the OHD server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the OHD server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the OHD server."


def get_start_command(server):
    """Build the command used to launch an OHD dedicated server."""

    executable = _resolve_executable_name(server)
    command = ["./" + executable]

    if executable.endswith("HarshDoorstopServer-Linux-Shipping"):
        command.extend(
            [
                "HarshDoorstop",
                gamemodule_common.build_unreal_travel_arg(
                    server.data.get("map") or "AAS-TestMap",
                    optional_options=(
                        ("MaxPlayers", server.data.get("maxplayers") or "16"),
                    ),
                ),
            ]
        )

    command.extend(
        [
            "-Port={}".format(server.data["port"]),
            "-QueryPort={}".format(server.data["queryport"]),
            "-SteamServerName={}".format(
                server.data.get("servername") or "Harsh Doorstop Dedicated Server"
            ),
            "-log",
        ]
    )
    return (command, server.data["dir"])


def get_query_address(server):
    """Return Operation: Harsh Doorstop's validated query endpoint."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the address used by Operation: Harsh Doorstop's info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop the OHD server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed OHD status is not implemented yet."""


def message(server, msg):
    """OHD has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an OHD server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported OHD datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )


def get_runtime_requirements(server):
    """Return Operation: Harsh Doorstop's native Linux Docker contract."""

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
            {"key": "queryport", "protocol": "udp"},
            {"key": "port", "protocol": "udp"},
        ),
        mounts=mounts,
    )


def get_container_spec(server):
    """Run Operation: Harsh Doorstop in Docker as the mounted server owner."""

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
