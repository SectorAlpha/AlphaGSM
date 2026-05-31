"""Humanitz dedicated server lifecycle helpers."""

import configparser
import os
import shutil

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

from utils.platform_info import IS_LINUX
import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2728330
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Humanitz in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Humanitz dedicated server to the latest version.",
    "Restart the Humanitz dedicated server.",
)
command_functions = {}
max_stop_wait = 1
DEFAULT_EXECUTABLES = (
    "HumanitZServer/Binaries/Win64/HumanitZServer-Win64-Shipping.exe",
    "HumanitZServer.exe",
)
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port for the server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-port={value}",
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        description="The query port for the server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-queryport={value}",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised server name.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-steamservername={value}",
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="The maximum number of players.",
        value_type="integer",
        apply_to=("datastore",),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}
config_sync_keys = ("servername", "maxplayers")


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


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="HumanitZServer/Binaries/Win64/HumanitZServer-Win64-Shipping.exe",
):
    """Collect and store configuration values for a Humanitz server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27016",
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": "16",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["HumanitZServer", "HumanitZServer/Saved"],
        targets=["HumanitZServer", "HumanitZServer/Saved"],
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
        prompt="Where would you like to install the Humanitz server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _resolve_executable_name(server):
    """Return the real dedicated executable from the installed Windows payload."""

    configured = server.data.get("exe_name")
    candidates = []
    if configured:
        candidates.append(configured)
    candidates.extend(name for name in DEFAULT_EXECUTABLES if name not in candidates)

    for candidate in candidates:
        if os.path.isfile(os.path.join(server.data["dir"], candidate)):
            return candidate
    raise ServerError("Executable file not found")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Humanitz server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def sync_server_config(server):
    """Mirror staged HumanitZ settings into GameServerSettings.ini."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return
    config_dir = os.path.join(server_dir, "HumanitZServer")
    ref_path = os.path.join(config_dir, "REF_GameServerSettings.ini")
    config_path = os.path.join(config_dir, "GameServerSettings.ini")

    if not os.path.isfile(config_path) and os.path.isfile(ref_path):
        shutil.copy2(ref_path, config_path)
    if not os.path.isfile(config_path):
        return

    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    parser.read(config_path)
    if not parser.has_section("Host Settings"):
        parser.add_section("Host Settings")
    parser.set(
        "Host Settings",
        "ServerName",
        '"{}"'.format(server.data.get("servername") or "HumanitZ [Dedicated]"),
    )
    parser.set(
        "Host Settings",
        "MaxPlayers",
        str(server.data.get("maxplayers") or "16"),
    )
    with open(config_path, "w", encoding="utf-8") as handle:
        parser.write(handle)


def prestart(server):
    """Stage HumanitZ runtime config before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for HumanitZ."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "udp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for HumanitZ."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Humanitz dedicated server."""

    executable = _resolve_executable_name(server)
    cmd = [
        executable,
        "-log",
        "-port={}".format(server.data["port"]),
        "-queryport={}".format(server.data["queryport"]),
        "-steamservername={}".format(
            server.data.get("servername") or "HumanitZ [Dedicated]"
        ),
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Humanitz by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Humanitz status is not implemented yet."""


def message(server, msg):
    """Humanitz has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Humanitz server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Humanitz datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'udp'}),
        extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'udp'}),
        extra_env=_container_runtime_env,
)
