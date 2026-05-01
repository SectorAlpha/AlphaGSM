"""Longvinter dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1639880
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Longvinter server",
    "The directory to install Longvinter in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Longvinter dedicated server to the latest version.",
    "Restart the Longvinter dedicated server.",
)
command_functions = {}
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
    "maxplayers": SettingSpec(canonical_key="maxplayers", description="Maximum allowed players."),
    "servername": SettingSpec(canonical_key="servername", description="Configured public server name."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="LongvinterServer.sh"):
    """Collect and store configuration values for a Longvinter server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "32",
            "servername": "Unnamed Island",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Longvinter/Saved/Config/LinuxServer", "Longvinter/Saved/SaveGames"],
        targets=["Longvinter/Saved/Config/LinuxServer", "Longvinter/Saved/SaveGames"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    server.data.setdefault("queryport", str(server.data["port"] + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Longvinter server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Longvinter server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Longvinter server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Longvinter server."


def get_start_command(server):
    """Build the command used to launch a Longvinter dedicated server."""

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
            *dynamic_args,
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the A2S query address for the Longvinter dedicated query port."""
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def do_stop(server, j):
    """Stop Longvinter using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Longvinter status is not implemented yet."""


def message(server, msg):
    """Longvinter has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Longvinter server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Longvinter datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("maxplayers", "servername", "exe_name", "dir", "queryport"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
)
