"""Soulmask dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3017300
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Soulmask server",
    "The directory to install Soulmask in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Soulmask dedicated server to the latest version.",
    "Restart the Soulmask dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        positional_key="level",
        include_maxplayers=True,
        include_servername=True,
        servername_format="-SteamServerName={value}",
    ),
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Administrator password.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-adminpsw={value}",
        secret=True,
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Server password.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-PSW={value}",
        secret=True,
    ),
    "bindaddress": SettingSpec(
        canonical_key="bindaddress",
        description="Hosted IP address to bind for launch.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-MULTIHOME={value}",
    ),
    "echoport": SettingSpec(
        canonical_key="echoport",
        description="Echo service port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-EchoPort={value}",
    ),
    "savinginterval": SettingSpec(
        canonical_key="savinginterval",
        description="Autosave interval in seconds.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-saving={value}",
    ),
    "backupinterval": SettingSpec(
        canonical_key="backupinterval",
        description="Backup interval in seconds.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-backup={value}",
    ),
    "mods": SettingSpec(canonical_key="mods", description="Optional mod list."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="WSServer.sh"):
    """Collect and store configuration values for a Soulmask server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "echoport": "18888",
            "servername": "AlphaGSM %s" % (server.name,),
            "level": "Level01_Main",
            "adminpassword": "alphagsm",
            "serverpassword": "",
            "maxplayers": "10",
            "bindaddress": "0.0.0.0",
            "backupinterval": "900",
            "savinginterval": "600",
            "mods": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["WS/Saved"],
        targets=["WS/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=8777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Soulmask server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Soulmask server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Soulmask server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Soulmask server."


def get_start_command(server):
    """Build the command used to launch a Soulmask dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        {
            "level": setting_schema["level"],
            "servername": setting_schema["servername"],
            "maxplayers": setting_schema["maxplayers"],
            "serverpassword": setting_schema["serverpassword"],
            "adminpassword": setting_schema["adminpassword"],
            "bindaddress": setting_schema["bindaddress"],
            "port": setting_schema["port"],
            "queryport": setting_schema["queryport"],
            "echoport": setting_schema["echoport"],
            "savinginterval": setting_schema["savinginterval"],
            "backupinterval": setting_schema["backupinterval"],
        },
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    command = [
        "./" + server.data["exe_name"],
        *dynamic_args[:1],
        "-server",
        "-log",
        "-forcepassthrough",
        "-UTF8Output",
        *dynamic_args[1:],
    ]
    if server.data["mods"]:
        command.append('-mod="%s"' % (server.data["mods"],))
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Soulmask using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Soulmask status is not implemented yet."""


def message(server, msg):
    """Soulmask has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Soulmask server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Soulmask datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "echoport", "maxplayers", "backupinterval", "savinginterval"),
        resolved_str_keys=(
            "servername",
            "level",
            "adminpassword",
            "serverpassword",
            "bindaddress",
            "mods",
            "exe_name",
            "dir",
        ),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'echoport', 'protocol': 'udp'}, {'key': 'echoport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'echoport', 'protocol': 'udp'}, {'key': 'echoport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
