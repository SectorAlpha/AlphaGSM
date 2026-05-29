"""Blackwake dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.simple_kv_config import rewrite_equals_config

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 423410
steam_anonymous_login_possible = True
DEFAULT_SERVER_PASSWORD = "alphagsm123"
DEFAULT_GAMEMODE = "7"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Blackwake server",
    "The directory to install Blackwake in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Blackwake dedicated server to the latest version.",
    "Restart the Blackwake dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "servername", "serverpassword", "gamemode")


def configure(server, ask, port=None, dir=None, *, exe_name="BlackwakeServer.exe"):
    """Collect and store configuration values for a Blackwake server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "maxplayers": "54",
            "servername": server.name,
            "serverpassword": DEFAULT_SERVER_PASSWORD,
            "gamemode": DEFAULT_GAMEMODE,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Blackwake_Data", "save", "config"],
        targets=["save", "config"],
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
        prompt="Where would you like to install the Blackwake server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _server_cfg_path(server):
    """Return the dedicated server config path."""

    return os.path.join(server.data["dir"], "Server.cfg")


def sync_server_config(server):
    """Keep the managed Blackwake server config aligned with AlphaGSM data."""

    config_path = _server_cfg_path(server)
    if not os.path.isfile(config_path):
        return
    rewrite_equals_config(
        config_path,
        {
            "serverName": server.data.get("servername", server.name),
            "port": int(server.data.get("port", 7777)),
            "sport": int(server.data.get("queryport", 27015)),
            "password": server.data.get("serverpassword", DEFAULT_SERVER_PASSWORD),
            # Keep the dedicated server on the documented dedicated-mode default
            # instead of letting headless Wine/Proton fall into Siege startup.
            "gamemode": int(server.data.get("gamemode", DEFAULT_GAMEMODE)),
            # Headless Wine/Proton runs are stable when we avoid spawning bot crews.
            "useBots": 0 if server.data.get("serverpassword") else 1,
        },
    )


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
_base_install.__doc__ = "Download the Blackwake server files via SteamCMD."


def install(server):
    """Download the Blackwake server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Blackwake server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Blackwake server."


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows server command for headless Linux hosts."""

    wrapped = proton.wrap_command(command, wineprefix=wineprefix)
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = proton.prepend_env_assignments(
        wrapped,
        SDL_VIDEODRIVER="x11",
        SDL_AUDIODRIVER="dummy",
    )
    wrapped = [
        arg
        for arg in wrapped
        if not (
            arg.startswith("DISPLAY=")
            or arg.startswith("WINEDLLOVERRIDES=")
        )
    ]
    return ["xvfb-run", "-a", *wrapped]


def get_start_command(server):
    """Build the command used to launch a Blackwake dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    # -batchmode -nographics suppress the Unity launcher GUI / splash screen so
    # no X11 window appears when running under Wine.
    cmd = [
        server.data["exe_name"],
        "-batchmode",
        "-nographics",
        "-port",
        str(server.data["port"]),
        "-queryport",
        str(server.data["queryport"]),
        "-maxplayers",
        str(server.data["maxplayers"]),
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


def prestart(server):
    """Refresh the dedicated server config before each launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the Steam query endpoint for Blackwake."""

    return (
        runtime_module.resolve_query_host(server),
        int(server.data["queryport"]),
        "a2s",
    )


def get_info_address(server):
    """Return the info endpoint for Blackwake."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Blackwake by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Blackwake status is not implemented yet."""


def message(server, msg):
    """Blackwake has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Blackwake server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Blackwake datastore edits."""

    if key == ("serverpassword",):
        password = "".join(value)
        if password and len(password) < 4:
            raise ServerError("serverpassword must be at least 4 characters or empty")
        return password
    if key == ("gamemode",):
        gamemode = int("".join(value))
        if gamemode < 1 or gamemode > 8:
            raise ServerError("gamemode must be between 1 and 8")
        return gamemode
    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("exe_name", "dir", "servername"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
