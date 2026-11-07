"""Night of the Dead dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import build_launch_arg_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1420710
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Night of the Dead server",
    "The directory to install Night of the Dead in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Night of the Dead dedicated server to the latest version.",
    "Restart the Night of the Dead dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ()
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _container_runtime_env(_server):
    """Return Docker runtime env for the shared wine-proton entrypoint."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 1024x768x24 -nolisten tcp",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }


def configure(server, ask, port=None, dir=None, *, exe_name="LFServer.exe"):
    """Collect and store configuration values for a Night of the Dead server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"queryport": "27015"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["LF/Saved", "ServerSettings.ini"],
        targets=["LF/Saved", "ServerSettings.ini"],
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
        prompt="Where would you like to install the Night of the Dead server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Night of the Dead server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def get_query_address(server):
    """Return the validated runtime query surface for Night of the Dead."""

    if IS_LINUX:
        return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the address used by AlphaGSM info for Night of the Dead."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Night of the Dead dedicated server."""

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
            "?listen",
            *dynamic_args,
            "-log",
            "-CRASHREPORTS",
        ]
    if IS_LINUX:
        cmd.insert(2, "-DisableAntiCheat")
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Night of the Dead using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def sync_server_config(server):
    """Mirror the root ServerSettings.ini into LF/Saved/Config before start."""

    root_config = os.path.join(server.data["dir"], "ServerSettings.ini")
    if not os.path.isfile(root_config):
        return
    target_dir = os.path.join(server.data["dir"], "LF", "Saved", "Config")
    os.makedirs(target_dir, exist_ok=True)
    shutil.copy2(root_config, os.path.join(target_dir, "ServerSettings.ini"))


def prestart(server):
    """Stage Night of the Dead's runtime config before launch."""

    sync_server_config(server)


def status(server, verbose):
    """Detailed Night of the Dead status is not implemented yet."""


def message(server, msg):
    """Night of the Dead has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Night of the Dead server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Night of the Dead datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_env=_container_runtime_env,
)
