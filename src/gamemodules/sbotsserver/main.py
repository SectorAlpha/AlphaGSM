"""StickyBots dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import build_launch_arg_values

import server.runtime as runtime_module
from utils.archive_install import ensure_executable
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 974130
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the StickyBots server",
    "The directory to install StickyBots in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the StickyBots dedicated server to the latest version.",
    "Restart the StickyBots dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _ensure_launch_files_executable(server):
    for relative_path in (
        server.data.get("exe_name", "blank1Server.sh"),
        "blank1/Binaries/Linux/blank1Server-Linux-Shipping",
    ):
        path = os.path.join(server.data["dir"], relative_path)
        if os.path.isfile(path):
            ensure_executable(path)


def configure(server, ask, port=None, dir=None, *, exe_name="blank1Server.sh"):
    """Collect and store configuration values for a StickyBots server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"queryport": "27015"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["blank1/Saved", "blank1Server.sh"],
        targets=["blank1/Saved", "blank1Server.sh"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    server.data.setdefault("queryport", "27015")
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the StickyBots server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_ensure_launch_files_executable,
)
install.__doc__ = "Download the StickyBots server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_ensure_launch_files_executable,
)
update.__doc__ = "Update the StickyBots server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the StickyBots dedicated server."


def get_start_command(server):
    """Build the command used to launch a StickyBots dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        [
            "./" + server.data["exe_name"],
            "-MultiHome=0.0.0.0",
            *dynamic_args,
            "-log",
            "-unattended",
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the A2S query address for StickyBots."""

    return runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Return the A2S info address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop StickyBots by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed StickyBots status is not implemented yet."""


def message(server, msg):
    """StickyBots has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a StickyBots server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported StickyBots datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
    ),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
    ),
    stdin_open=True,
)