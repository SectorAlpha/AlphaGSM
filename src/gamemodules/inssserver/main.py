"""Insurgency: Sandstorm dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 581330
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Insurgency: Sandstorm in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Insurgency: Sandstorm dedicated server to the latest version.",
    "Restart the Insurgency: Sandstorm dedicated server.",
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
    "hostname": SettingSpec(
        canonical_key="hostname",
        description="Server hostname shown in the browser.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-hostname={value}",
    ),
    "mapcycle": SettingSpec(canonical_key="mapcycle", description="Initial scenario or mapcycle entry."),
    "maxplayers": SettingSpec(canonical_key="maxplayers", description="Maximum allowed players.", value_type="integer"),
    "gslt": SettingSpec(canonical_key="gslt", description="Optional game server login token."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="Insurgency/Binaries/Linux/InsurgencyServer-Linux-Shipping"):
    """Collect and store configuration values for an Insurgency: Sandstorm server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "mapcycle": "Scenario_Crossing_Push_Security",
            "hostname": "AlphaGSM %s" % (server.name,),
            "maxplayers": "28",
            "gslt": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Insurgency/Config/Server", "Insurgency/Saved"],
        targets=["Insurgency/Config/Server", "Insurgency/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27102,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", str(int(server.data["port"]) + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Insurgency: Sandstorm server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Insurgency: Sandstorm server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Insurgency: Sandstorm server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Insurgency: Sandstorm server."


def get_query_address(server):
    """Insurgency: Sandstorm uses Steam A2S on the dedicated query port."""
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_start_command(server):
    """Build the command used to launch an Insurgency: Sandstorm server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        {
            "port": setting_schema["port"],
            "queryport": setting_schema["queryport"],
            "hostname": setting_schema["hostname"],
        },
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    cmd = [
        "./" + server.data["exe_name"],
        "%s?MaxPlayers=%s" % (server.data["mapcycle"], server.data["maxplayers"]),
        *dynamic_args,
        "-log",
    ]
    if server.data.get("gslt"):
        cmd.append("-GSLTToken=%s" % (server.data["gslt"],))
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Insurgency: Sandstorm by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Insurgency: Sandstorm status is not implemented yet."""


def message(server, msg):
    """Insurgency: Sandstorm has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Insurgency: Sandstorm server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Insurgency: Sandstorm datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("mapcycle", "hostname", "gslt", "exe_name", "dir"),
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
