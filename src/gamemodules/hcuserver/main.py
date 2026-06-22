"""HYPERCHARGE: Unboxed dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import build_launch_arg_values

import server.runtime as runtime_module
from utils.archive_install import ensure_executable
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1045940
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the HYPERCHARGE: Unboxed server",
    "The directory to install HYPERCHARGE: Unboxed in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the HYPERCHARGE: Unboxed dedicated server to the latest version.",
    "Restart the HYPERCHARGE: Unboxed dedicated server.",
)
command_functions = {}
max_stop_wait = 1
ignored_port_keys = ("queryport",)
_unreal_setting_schema = gamemodule_common.build_unreal_setting_schema()
_unreal_setting_schema.pop("queryport", None)
setting_schema = {
    **_unreal_setting_schema,
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _ensure_launch_files_executable(server):
    for relative_path in (
        server.data.get("exe_name", "UnboxedServer.sh"),
        "Unboxed/Binaries/Linux/UnboxedServer-Linux-Shipping",
    ):
        path = os.path.join(server.data["dir"], relative_path)
        if os.path.isfile(path):
            ensure_executable(path)


def configure(server, ask, port=None, dir=None, *, exe_name="UnboxedServer.sh"):
    """Collect and store configuration values for a HYPERCHARGE server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    server.data.pop("queryport", None)
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Unboxed/Saved", "UnboxedServer.sh"],
        targets=["Unboxed/Saved", "UnboxedServer.sh"],
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
        prompt="Where would you like to install the HYPERCHARGE: Unboxed server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_ensure_launch_files_executable,
)
install.__doc__ = "Download the HYPERCHARGE: Unboxed server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_ensure_launch_files_executable,
)
update.__doc__ = "Update the HYPERCHARGE: Unboxed server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the HYPERCHARGE: Unboxed dedicated server."


def get_start_command(server):
    """Build the command used to launch a HYPERCHARGE: Unboxed dedicated server."""

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
    """Return the generic UDP probe address for HYPERCHARGE: Unboxed."""

    return runtime_module.resolve_query_host(server), int(server.data["port"]), "udp"


def get_info_address(server):
    """Return the generic UDP info address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop HYPERCHARGE: Unboxed by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed HYPERCHARGE: Unboxed status is not implemented yet."""


def message(server, msg):
    """HYPERCHARGE: Unboxed has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a HYPERCHARGE: Unboxed server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported HYPERCHARGE: Unboxed datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=(
        {"key": "port", "protocol": "udp"},
    ),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
    ),
    stdin_open=True,
)