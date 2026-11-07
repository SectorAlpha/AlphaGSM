"""Killing Floor 2 dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from server.modsupport.native_workshop import build_native_workshop_support
from .workshop import configure_workshop, validate_installed_map

steam_app_id = 232130
steam_anonymous_login_possible = True
workshop_app_id = 232090

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Killing Floor 2 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Killing Floor 2 dedicated server to the latest version.",
    "Restart the Killing Floor 2 dedicated server.",
)
command_functions = {}
_mod_support = build_native_workshop_support(
    game_label="Killing Floor 2", workshop_app_id=workshop_app_id,
    apply_callback=configure_workshop,
)
commands += _mod_support.commands
command_args.update(_mod_support.command_args)
command_descriptions.update(_mod_support.command_descriptions)
command_functions.update(_mod_support.command_functions)
ensure_mod_state = _mod_support.ensure_mod_state
apply_configured_mods = _mod_support.apply_configured_mods
cleanup_configured_mods = _mod_support.cleanup_configured_mods
max_stop_wait = 1
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="Primary gameplay port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-Port={value}",
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        description="Steam query port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-QueryPort={value}",
    ),
    "startmap": SettingSpec(canonical_key="startmap", description="Starting map name."),
    "gametype": SettingSpec(canonical_key="gametype", description="Game mode class to start."),
    "configsubdir": SettingSpec(canonical_key="configsubdir", description="Relative config directory."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Win64/KFGameSteamServer.bin.x86_64"):
    """Collect and store configuration values for a Killing Floor 2 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "startmap": "KF-BioticsLab",
            "gametype": "KFGameContent.KFGameInfo_Survival",
            "configsubdir": "KFGame/Config",
            "queryport": 27015,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["KFGame", "Binaries"],
        targets=["KFGame"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Killing Floor 2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the dedicated server and reconcile native Workshop subscriptions."""
    _install(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


def prestart(server):
    """Configure native downloads and client delivery while the server is stopped."""
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Killing Floor 2 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Killing Floor 2 server."


def get_start_command(server):
    """Build the command used to launch a Killing Floor 2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        {"port": setting_schema["port"], "queryport": setting_schema["queryport"]},
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        [
            "./" + server.data["exe_name"],
            "%s?Game=%s" % (server.data["startmap"], server.data["gametype"]),
            *dynamic_args,
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return Killing Floor 2's separate Steam query endpoint."""

    return (
        runtime_module.resolve_query_host(server),
        int(server.data["queryport"]),
        "a2s",
    )


def get_info_address(server):
    """Use the Steam query endpoint for structured server information."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Killing Floor 2 using the standard exit command."""

    runtime_module.send_to_server(server, "\nexit\n")


def status(server, verbose):
    """Detailed Killing Floor 2 status is not implemented yet."""


def message(server, msg):
    """Killing Floor 2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Killing Floor 2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Killing Floor 2 datastore edits."""

    if key == ["startmap"]:
        return validate_installed_map(server, " ".join(value), game_dir="KFGame",
                                      suffix=".kfm", stock="KF-BioticsLab")
    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("startmap", "gametype", "configsubdir", "exe_name", "dir"),
        backup_module=backup_utils,
    )

_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "queryport", "protocol": "udp"},
    {"key": "port", "offset": 12783, "protocol": "udp"},
)
port_claim_definitions = _PORT_DEFINITIONS


def get_runtime_requirements(server):
    """Declare native Linux execution and its managed gameplay and query ports."""
    return runtime_module.build_runtime_requirements(
        server, family="steamcmd-linux", port_definitions=_PORT_DEFINITIONS,
    )


def get_container_spec(server):
    """Launch the native dedicated server through the shared runtime family."""
    return runtime_module.build_container_spec(
        server, family="steamcmd-linux", get_start_command=get_start_command,
        port_definitions=_PORT_DEFINITIONS, stdin_open=True,
    )
