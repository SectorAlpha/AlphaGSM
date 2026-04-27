"""Call of Duty: Modern Warfare 3 dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 115310
steam_anonymous_login_possible = False

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Modern Warfare 3 server",
    "The directory to install Modern Warfare 3 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Modern Warfare 3 dedicated server to the latest version.",
    "Restart the Modern Warfare 3 dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "hostname": SettingSpec(
        canonical_key="hostname",
        description="The advertised server name.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+set", "sv_hostname"),
    ),
    "port": SettingSpec(
        canonical_key="port",
        value_type="integer",
        description="The game port for the server.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+set", "net_port"),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        value_type="integer",
        description="The maximum number of players.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+set", "sv_maxclients"),
    ),
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=("map",),
        description="The startup map.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+map",),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="iw5mp_server.exe"):
    """Collect and store configuration values for a Modern Warfare 3 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "mp_alpha",
            "maxplayers": "18",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["main", "players2", "zone"],
        targets=["main", "players2", "zone"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27016,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Modern Warfare 3 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Modern Warfare 3 server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Modern Warfare 3 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Modern Warfare 3 server."


def get_start_command(server):
    """Build the command used to launch a Modern Warfare 3 dedicated server."""

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
    """Stop Modern Warfare 3 by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Modern Warfare 3 status is not implemented yet."""


def message(server, msg):
    """Modern Warfare 3 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Modern Warfare 3 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Modern Warfare 3 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("hostname", "startmap", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
