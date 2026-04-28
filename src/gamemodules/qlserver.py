"""Quake Live dedicated server lifecycle helpers."""

import os

import screen
import server.runtime as runtime_module
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from utils.simple_kv_config import rewrite_equals_config

steam_app_id = 349090
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Quake Live in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Quake Live dedicated server to the latest version.",
    "Restart the Quake Live dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "startmap")
_quake_launch_schema = gamemodule_common.build_quake_setting_schema(
    port_tokens=("+set", "net_port"),
    hostname_tokens=("+set", "sv_hostname"),
)
setting_schema = {
    "homepath": SettingSpec(
        canonical_key="homepath",
        description="Launch-only homepath for Quake Live.",
        apply_to=("launch_args",),
        storage_key="dir",
        launch_arg_tokens=("+set", "fs_homepath"),
    ),
    "port": _quake_launch_schema["port"],
    "hostname": SettingSpec(
        canonical_key="hostname",
        aliases=("servername",),
        description=_quake_launch_schema["hostname"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="hostname",
        launch_arg_tokens=_quake_launch_schema["hostname"].launch_arg_tokens,
    ),
    "servercfg": SettingSpec(
        canonical_key="servercfg",
        description="Server config file to exec on startup.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+exec",),
    ),
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=_quake_launch_schema["startmap"].aliases,
        description=_quake_launch_schema["startmap"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="startmap",
        launch_arg_tokens=_quake_launch_schema["startmap"].launch_arg_tokens,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="qzeroded.x64"):
    """Collect and store configuration values for a Quake Live server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "campgrounds",
            "servercfg": "baseq3/server.cfg",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["baseq3", "steam_appid.txt"],
        targets=["baseq3"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27960,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Quake Live server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=lambda server: sync_server_config(server),
)
install.__doc__ = "Download the Quake Live dedicated server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=lambda server: sync_server_config(server),
)

restart = gamemodule_common.make_restart_hook()


def sync_server_config(server):
    """Rewrite managed Quake Live config entries from datastore values."""

    config_relpath = server.data.get("servercfg", "baseq3/server.cfg")
    config_path = os.path.join(server.data["dir"], config_relpath)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "campgrounds",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            '"%s"' % (str(current_value),)
            if spec.canonical_key == "hostname"
            else str(current_value)
        ),
    )
    rewrite_equals_config(config_path, config_values)


def get_start_command(server):
    """Build the command used to launch a Quake Live dedicated server."""

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
    """Return Docker runtime metadata for SteamCMD-backed Linux-native servers."""

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
    """Return the Docker launch spec for Quake Live."""

    requirements = get_runtime_requirements(server)
    launch_args = build_launch_arg_values(
        dict(server.data, dir="/srv/server"),
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": ["./" + server.data["exe_name"], *launch_args],
    }


def get_query_address(server):
    """Return the Quake UDP query address used by the qlserver module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the qlserver module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Quake Live using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Quake Live status is not implemented yet."""


def message(server, msg):
    """Quake Live has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake Live server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Quake Live datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("hostname", "startmap", "servercfg", "exe_name", "dir"),
        backup_module=backup_utils,
    )
