"""Tower Unite dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 439660
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Tower Unite server",
    "The directory to install Tower Unite in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Tower Unite dedicated server to the latest version.",
    "Restart the Tower Unite dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _config_name(server):
    return "%s.ini" % (server.name,)


def _config_dir(server):
    return os.path.join(server.data["dir"], "Tower", "Binaries", "Linux")


def _config_path(server):
    return os.path.join(_config_dir(server), _config_name(server))


def _default_config_path(server):
    return os.path.join(_config_dir(server), "TowerServer.ini")


def _ensure_instance_config(server):
    config_path = _config_path(server)
    if os.path.isfile(config_path):
        return
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    default_config_path = _default_config_path(server)
    if os.path.isfile(default_config_path):
        shutil.copyfile(default_config_path, config_path)
        return
    with open(config_path, "a", encoding="utf-8"):
        pass


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="Tower/Binaries/Linux/TowerServer-Linux-Shipping",
):
    """Collect and store configuration values for a Tower Unite server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"queryport": "27015"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Tower/Binaries/Linux", "Tower/Saved/Logs"],
        targets=["Tower/Binaries/Linux", "Tower/Saved/Logs"],
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
        prompt="Where would you like to install the Tower Unite server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=_ensure_instance_config,
)
install.__doc__ = "Download the Tower Unite server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=_ensure_instance_config,
)
update.__doc__ = "Update the Tower Unite server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Tower Unite server."


def get_start_command(server):
    """Build the command used to launch a Tower Unite dedicated server."""

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
            "-TowerServerINI=%s" % (_config_name(server),),
            "-log",
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the A2S query address for the Tower Unite dedicated query port."""

    return runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Tower Unite by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Tower Unite status is not implemented yet."""


def message(server, msg):
    """Tower Unite has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Tower Unite server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Tower Unite datastore edits."""

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