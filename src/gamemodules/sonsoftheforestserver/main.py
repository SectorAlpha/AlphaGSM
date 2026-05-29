"""Sons Of The Forest dedicated server lifecycle helpers."""

import json
import os
import shutil
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2465200
steam_anonymous_login_possible = True
DEFAULT_PORT = 8766
DEFAULT_QUERYPORT = 27016
DEFAULT_BLOBSYNCPORT = 9700
_CLIENT_STEAM_APP_ID = "1326470"
_USERDATA_DIR = "user-data"
_DEFAULT_OWNERS_WHITELIST = """# In order to be able to administrate your server from in game directly, you will need to setup server ownership.
# Add below the steam ids of every server owner, one steam id per line.
# To find your SteamID, open Steam and click on your name on the top right, then go to Account Details.
# You can use # to comment out a line. That can be helpful to keep track of SteamIDs, you can include their name in the line above or below, starting with a #.

"""

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Sons Of The Forest server",
    "The directory to install Sons Of The Forest in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Sons Of The Forest dedicated server to the latest version.",
    "Restart the Sons Of The Forest dedicated server.",
)
command_functions = {}
max_stop_wait = 1
_PREFERRED_EXE_NAME = "SonsOfTheForestDS.exe"
_LEGACY_BATCH_LAUNCHER = "StartSOTFDedicated.bat"
config_sync_keys = ("port", "queryport", "blobsyncport")
_XVFB_SERVER_ARGS = "-screen 0 1024x768x24 -nolisten tcp"


def configure(server, ask, port=None, dir=None, *, exe_name=_PREFERRED_EXE_NAME):
    """Collect and store configuration values for a Sons Of The Forest server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": str(DEFAULT_QUERYPORT),
            "blobsyncport": str(DEFAULT_BLOBSYNCPORT),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=[_USERDATA_DIR],
        targets=[_USERDATA_DIR],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=DEFAULT_PORT,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Sons Of The Forest server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _user_data_dir(server):
    """Return the managed Sons Of The Forest user-data folder."""

    return os.path.join(server.data["dir"], _USERDATA_DIR)


def _config_path(server):
    """Return the managed dedicatedserver.cfg path."""

    return os.path.join(_user_data_dir(server), "dedicatedserver.cfg")


def _steam_appid_path(server):
    """Return the managed steam_appid.txt path."""

    return os.path.join(server.data["dir"], "steam_appid.txt")


def _owners_whitelist_path(server):
    """Return the managed owners whitelist path."""

    return os.path.join(_user_data_dir(server), "ownerswhitelist.txt")


def _log_path():
    """Return the relative managed server log path."""

    return os.path.join(_USERDATA_DIR, "logs", "sotf_log.txt")


def _default_config_payload(server):
    """Return the managed dedicatedserver.cfg payload."""

    return {
        "IpAddress": "0.0.0.0",
        "GamePort": int(server.data.get("port", DEFAULT_PORT)),
        "QueryPort": int(server.data.get("queryport", DEFAULT_QUERYPORT)),
        "BlobSyncPort": int(server.data.get("blobsyncport", DEFAULT_BLOBSYNCPORT)),
        "ServerName": server.name,
        "MaxPlayers": 8,
        "Password": "",
        "LanOnly": False,
        "SaveSlot": 1,
        "SaveMode": "Continue",
        "GameMode": "Normal",
        "SaveInterval": 600,
        "IdleDayCycleSpeed": 0.0,
        "IdleTargetFramerate": 5,
        "ActiveTargetFramerate": 60,
        "LogFilesEnabled": True,
        "TimestampLogFilenames": False,
        "TimestampLogEntries": True,
        "SkipNetworkAccessibilityTest": True,
        "GameSettings": {},
        "CustomGameModeSettings": {},
    }


def sync_server_config(server):
    """Write the managed dedicatedserver.cfg into the user-data directory."""

    config_path = _config_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(_default_config_payload(server), handle, indent=2)
        handle.write("\n")
    with open(_steam_appid_path(server), "w", encoding="ascii") as handle:
        handle.write(_CLIENT_STEAM_APP_ID + "\n")
    owners_whitelist_path = _owners_whitelist_path(server)
    if not os.path.exists(owners_whitelist_path):
        with open(owners_whitelist_path, "w", encoding="utf-8") as handle:
            handle.write(_DEFAULT_OWNERS_WHITELIST)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Sons Of The Forest server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Sons Of The Forest server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Sons Of The Forest server."


def prestart(server):
    """Refresh dedicatedserver.cfg before launching the dedicated server."""

    sync_server_config(server)


def _resolve_launch_executable(server):
    """Prefer the dedicated server executable over the legacy batch launcher."""

    configured_exe = server.data["exe_name"]
    if configured_exe != _LEGACY_BATCH_LAUNCHER:
        return configured_exe

    preferred_exe_path = os.path.join(server.data["dir"], _PREFERRED_EXE_NAME)
    if os.path.isfile(preferred_exe_path):
        return _PREFERRED_EXE_NAME

    return configured_exe


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows dedicated server command for Linux hosts."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
    )
    wrapped = proton.prepend_env_assignments(
        wrapped,
        LIBGL_ALWAYS_SOFTWARE="1",
        SteamAppId=_CLIENT_STEAM_APP_ID,
        SteamGameId=_CLIENT_STEAM_APP_ID,
    )
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = proton.prepend_env_assignments(
        wrapped,
        SDL_VIDEODRIVER="x11",
        SDL_AUDIODRIVER="dummy",
        WINEDLLOVERRIDES="",
    )
    wrapped = [
        arg
        for arg in wrapped
        if not (
            arg == "DISPLAY="
            or arg == "WINEDLLOVERRIDES=winex11.drv="
        )
    ]
    return [
        "xvfb-run",
        "-a",
        f"--server-args={_XVFB_SERVER_ARGS}",
        *wrapped,
    ]


def get_query_address(server):
    """Sons Of The Forest exposes Steam server discovery on its query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the same query address used for info()."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Sons Of The Forest dedicated server."""

    exe_name = _resolve_launch_executable(server)
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    # Under Wine/Xvfb the Unity dedicated server needs the explicit headless
    # flags to get past its batch-window startup and reach the live server
    # listener.
    cmd = [
        exe_name,
        "-userdatapath",
        f"./{_USERDATA_DIR}",
        "-batchmode",
        "-nographics",
        "-verboseLogging",
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


def _get_container_start_command(server):
    """Return the bare Windows command for the Docker wine-proton runtime."""

    exe_name = _resolve_launch_executable(server)
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return [
        exe_name,
        "-userdatapath",
        f"./{_USERDATA_DIR}",
        "-batchmode",
        "-nographics",
        "-verboseLogging",
    ], server.data["dir"]


def do_stop(server, j):
    """Stop Sons Of The Forest using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Sons Of The Forest status is not implemented yet."""


def message(server, msg):
    """Sons Of The Forest has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Sons Of The Forest server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Sons Of The Forest datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "blobsyncport"),
        str_keys=("exe_name", "dir"),
    )

def _container_runtime_env(_server):
    """Return Docker runtime env for the shared wine-proton entrypoint."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": _XVFB_SERVER_ARGS,
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "SteamAppId": _CLIENT_STEAM_APP_ID,
        "SteamGameId": _CLIENT_STEAM_APP_ID,
    }


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "blobsyncport", "protocol": "udp"},
    ),
    extra_env=_container_runtime_env,
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=_get_container_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "blobsyncport", "protocol": "udp"},
    ),
    extra_env=_container_runtime_env,
)
