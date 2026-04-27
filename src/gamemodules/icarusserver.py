"""Icarus dedicated server lifecycle helpers."""

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2089300
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Icarus server",
    "The directory to install Icarus in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Icarus dedicated server to the latest version.",
    "Restart the Icarus dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(include_servername=True),
    "worldname": SettingSpec(
        canonical_key="worldname",
        description="The world name used by the server.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-WorldName={value}",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="IcarusServer.exe"):
    """Collect and store configuration values for an Icarus server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "17778",
            "servername": "AlphaGSM %s" % (server.name,),
            "worldname": server.name,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved"],
        targets=["Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=17777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Icarus server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Icarus server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an Icarus dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    cmd = [
            server.data["exe_name"],
            *dynamic_args,
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Icarus using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


status = gamemodule_common.make_noop_status_hook()
status.__doc__ = "Detailed Icarus status is not implemented yet."


def message(server, msg):
    """Icarus has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Icarus server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Icarus datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("servername", "worldname", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
