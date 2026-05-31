"""The Isle dedicated server lifecycle helpers."""

import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 412680
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install The Isle in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update The Isle dedicated server to the latest version.",
    "Restart The Isle dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        positional_key="map",
        positional_description="The startup map.",
    ),
    "eos_client_id": SettingSpec(
        canonical_key="eos_client_id",
        description="Epic Online Services dedicated server client ID.",
        secret=True,
    ),
    "eos_client_secret": SettingSpec(
        canonical_key="eos_client_secret",
        description="Epic Online Services dedicated server client secret.",
        secret=True,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="TheIsleServer.sh"):
    """Collect and store configuration values for The Isle server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "7778",
            "map": "TheIsle",
            "eos_client_id": "",
            "eos_client_secret": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["TheIsle/Saved/Config", "TheIsle/Saved/Logs"],
        targets=["TheIsle/Saved/Config", "TheIsle/Saved/Logs"],
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
        prompt="Where would you like to install The Isle server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download The Isle server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch The Isle dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    eos_client_id = str(server.data.get("eos_client_id", "")).strip()
    eos_client_secret = str(server.data.get("eos_client_secret", "")).strip()
    if not eos_client_id or not eos_client_secret:
        gamemodule_common.raise_byo_requirement(
            "tiserver",
            "Epic Online Services dedicated server client credentials",
            actions=(
                "Set eos_client_id and eos_client_secret before starting the server",
                "Use the official dedicated-server guide to create TheIsle/Saved/Config/LinuxServer/Engine.ini if you prefer file-based EOS configuration",
            ),
            docs_slug="tiserver",
        )
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        [
            "./" + server.data["exe_name"],
            *dynamic_args,
            "-log",
            "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientId={}".format(eos_client_id),
            "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientSecret={}".format(eos_client_secret),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop The Isle by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed The Isle status is not implemented yet."""


def message(server, msg):
    """The Isle has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for The Isle server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported The Isle datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("map", "eos_client_id", "eos_client_secret", "exe_name", "dir"),
        backup_module=backup_utils,
    )

def get_runtime_requirements(server):
    """Return The Isle's native Linux Docker runtime contract."""

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
            {"key": "queryport", "protocol": "tcp"},
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        mounts=mounts,
    )


def get_container_spec(server):
    """Run The Isle as the mounted server-directory owner inside Docker."""

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
