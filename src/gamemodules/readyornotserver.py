"""Ready or Not dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values

from utils.platform_info import IS_LINUX
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 950290
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Ready or Not server",
    "The directory to install Ready or Not in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Ready or Not dedicated server to the latest version.",
    "Restart the Ready or Not dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("queryport", "maxplayers")
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(include_maxplayers=True),
    **gamemodule_common.build_executable_path_setting_schema(),
}
setting_schema["queryport"] = SettingSpec(
    canonical_key="queryport",
    description="The query port for the server.",
    value_type="integer",
    apply_to=("datastore", "launch_args", "native_config"),
    native_config_key="queryport",
    launch_arg_format="-QueryPort={value}",
    examples=("27015",),
)
setting_schema["maxplayers"] = SettingSpec(
    canonical_key="maxplayers",
    description="The maximum number of players.",
    value_type="integer",
    apply_to=("datastore", "launch_args", "native_config"),
    native_config_key="maxplayers",
    launch_arg_format="-MaxPlayers={value}",
    examples=("16",),
)


def _config_path(server):
    """Return the managed Ready or Not config path."""

    return os.path.join(server.data["dir"], "ReadyOrNot", "Config", "ServerConfig.ini")


def sync_server_config(server):
    """Write template-backed Ready or Not settings into ServerConfig.ini."""

    config_path = _config_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "queryport": int(server.data.get("port", 7777)) + 1,
            "maxplayers": 16,
        },
        value_transform=lambda _spec, value: str(value),
        require_explicit_key=True,
    )
    rewrite_equals_config(config_path, config_values)


def configure(server, ask, port=None, dir=None, *, exe_name="ReadyOrNotServer.exe"):
    """Collect and store configuration values for a Ready or Not server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"maxplayers": "16"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ReadyOrNot/Config", "ReadyOrNot/Saved"],
        targets=["ReadyOrNot/Config", "ReadyOrNot/Saved"],
    )
    resolved_port = gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    server.data.setdefault("queryport", str(int(resolved_port) + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Ready or Not server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Ready or Not server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Ready or Not dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    # -unattended prevents UE4 from opening dialogs or spawning GUI windows
    # under Wine when the engine hits an error or requires user interaction.
    cmd = [
        server.data["exe_name"],
        *dynamic_args,
        "-log",
        "-unattended",
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
    return cmd, server.data["dir"]


def get_query_address(server):
    """Return A2S query address for Ready or Not (queryport, not game port)."""
    return "127.0.0.1", int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Return A2S info address for Ready or Not (same as query address)."""
    return "127.0.0.1", int(server.data["queryport"]), "a2s"


def do_stop(server, j):
    """Stop Ready or Not by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
    return None
status.__doc__ = "Detailed Ready or Not status is not implemented yet."


def message(server, msg):
    """Ready or Not has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Ready or Not server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Ready or Not datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)
