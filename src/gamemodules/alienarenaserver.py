"""Alien Arena dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 629540
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Alien Arena in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Alien Arena server to the latest version.",
    "Restart the Alien Arena server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        game_key="game",
        game_description="The active Alien Arena game directory.",
        fs_game_tokens=("+set", "game"),
        port_tokens=("+set", "port"),
        hostname_tokens=("+set", "hostname"),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="crx-dedicated",
):
    """Collect and store configuration values for an Alien Arena server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "game": "arena",
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "dm-deathvalley",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["arena", "data1"],
        targets=["arena", "data1"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27910,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Alien Arena server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Alien Arena server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an Alien Arena dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for SteamCMD-backed Linux servers."""

    requirements = {
        "engine": "docker",
        "family": "steamcmd-linux",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Alien Arena."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def do_stop(server, j):
    """Stop Alien Arena using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Alien Arena status is not implemented yet."""


def message(server, msg):
    """Alien Arena has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Alien Arena server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Alien Arena datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("game", "exe_name", "dir", "startmap", "hostname"),
        backup_module=backup_utils,
    )
