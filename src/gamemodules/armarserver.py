"""Arma Reforger dedicated server lifecycle helpers."""

import json
import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import (
    SettingSpec,
    build_launch_arg_values,
    build_native_config_tree,
    merge_nested_config,
)
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1874900
steam_anonymous_login_possible = True
DEFAULT_SCENARIO_ID = "{ECC61978EDCC2B5A}Missions/23_Campaign.conf"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Arma Reforger in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Arma Reforger dedicated server to the latest version.",
    "Restart the Arma Reforger dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "maxplayers", "scenarioid", "bindaddress", "adminpassword")
setting_schema = {
    "map": SettingSpec(
        canonical_key="map",
        aliases=("scenario", "scenarioid"),
        description="The selected scenario file used by the server.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        storage_key="scenarioid",
        native_config_path=("game", "scenarioId"),
        examples=(DEFAULT_SCENARIO_ID,),
    ),
    "port": SettingSpec(
        canonical_key="port",
        description="The primary game port.",
        value_type="integer",
        apply_to=("datastore", "native_config", "launch_args"),
        launch_arg_tokens=("-bindPort",),
        examples=("2001",),
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        description="The A2S query port.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_path=("a2s", "port"),
        examples=("2002",),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum number of players allowed on the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_path=("game", "maxPlayers"),
        examples=("8",),
    ),
    "bindaddress": SettingSpec(
        canonical_key="bindaddress",
        description="IP address the server binds its A2S listener to.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        native_config_path=("a2s", "address"),
        launch_arg_tokens=("-bindAddress",),
        examples=("0.0.0.0",),
    ),
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Password used for administrative access.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        native_config_path=("game", "passwordAdmin"),
        secret=True,
    ),
}


def sync_server_config(server):
    """Write the managed Arma Reforger server config from datastore values."""

    config_dir = os.path.join(server.data["dir"], os.path.dirname(server.data["configfile"]))
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    os.makedirs(os.path.join(server.data["dir"], server.data["profilesdir"]), exist_ok=True)

    config_path = os.path.join(server.data["dir"], server.data["configfile"])
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                config = loaded
        except (json.JSONDecodeError, OSError):
            config = {}

    updates = build_native_config_tree(
        server.data,
        setting_schema,
        defaults={
            "bindaddress": "0.0.0.0",
            "queryport": int(server.data.get("port", 2001)) + 1,
            "maxplayers": 8,
            "scenarioid": DEFAULT_SCENARIO_ID,
        },
        value_transform=lambda spec, value: int(value) if spec.value_type == "integer" else str(value),
        require_explicit_path=True,
    )
    merge_nested_config(config, updates)

    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")


def configure(server, ask, port=None, dir=None, *, exe_name="ArmaReforgerServer"):
    """Collect and store configuration values for an Arma Reforger server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "configfile": "configs/server.json",
            "profilesdir": "profile",
            "bindaddress": "0.0.0.0",
            "adminpassword": "",
            "scenarioid": DEFAULT_SCENARIO_ID,
            "maxplayers": 8,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["configs", "profile"],
        targets=["configs", "profile"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=2001,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", int(server.data["port"]) + 1)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Arma Reforger server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Arma Reforger server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)
    server.data.save()


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Arma Reforger server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Arma Reforger server."


def _build_start_command(server):
    """Build the Arma Reforger start command without install-state checks."""

    config_path = os.path.join(server.data["dir"], server.data["configfile"])
    profile_path = os.path.join(server.data["dir"], server.data["profilesdir"])
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )
    return (
        [
            "./" + server.data["exe_name"],
            "-config",
            config_path,
            "-profile",
            profile_path,
            *launch_args,
        ],
        server.data["dir"],
    )


def get_start_command(server):
    """Build the command used to launch an Arma Reforger dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    config_path = os.path.join(server.data["dir"], server.data["configfile"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if not os.path.isfile(config_path):
        raise ServerError("Config file not found")
    return _build_start_command(server)


def get_runtime_requirements(server):
    """Return Docker runtime metadata for Arma Reforger."""

    requirements = {
        "engine": "docker",
        "family": "steamcmd-linux",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    ports = []
    for key in ("port", "queryport"):
        if key in server.data and server.data[key] is not None:
            ports.append(
                {
                    "host": int(server.data[key]),
                    "container": int(server.data[key]),
                    "protocol": "udp",
                }
            )
    if ports:
        requirements["ports"] = ports
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Arma Reforger."""

    cmd, _cwd = _build_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Return the A2S query address used by Arma Reforger."""

    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", int(server.data["port"]) + 1)), "a2s")


def get_info_address(server):
    """Return the A2S info address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Arma Reforger by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Arma Reforger status is not implemented yet."""


def message(server, msg):
    """Arma Reforger has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Arma Reforger server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Arma Reforger datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] == "queryport":
        return int(value[0])
    if key[0] == "maxplayers":
        return int(value[0])
    if key[0] == "scenarioid":
        return str(value[0])
    if key[0] in ("configfile", "profilesdir", "bindaddress", "adminpassword", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")
