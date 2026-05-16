"""Survive the Nights dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common
from utils.simple_kv_config import rewrite_equals_config

steam_app_id = 1502300
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Survive the Nights server",
    "The directory to install Survive the Nights in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Survive the Nights dedicated server to the latest version.",
    "Restart the Survive the Nights dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port for the Survive the Nights server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="Port",
    ),
}


def configure(server, ask, port=None, dir=None, *, exe_name="Server_Linux_x64"):
    """Collect and store configuration values for a Survive the Nights server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"configfile": "Config/ServerConfig.txt"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Config", "Saved"],
        targets=["Config", "Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=8888,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Survive the Nights server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Survive the Nights server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)


def sync_server_config(server):
    """Write the current port to ServerConfig.txt."""

    config_dir = os.path.join(server.data["dir"], "Config")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(
        server.data["dir"],
        server.data.get("configfile", "Config/ServerConfig.txt"),
    )
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={"port": 8888},
        require_explicit_key=True,
        value_transform=lambda _spec, current_value: str(int(current_value)),
    )
    rewrite_equals_config(config_path, config_values)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Survive the Nights server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Survive the Nights server."


def get_query_address(server):
    """Survive the Nights exposes A2S on the configured gameplay port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "a2s")


def get_info_address(server):
    """Return the A2S endpoint used by the info command."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "a2s")


def get_start_command(server):
    """Build the command used to launch a Survive the Nights dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Survive the Nights using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Survive the Nights status is not implemented yet."""


def message(server, msg):
    """Survive the Nights has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Survive the Nights server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Survive the Nights datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("configfile", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
