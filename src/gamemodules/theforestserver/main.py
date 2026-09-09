"""The Forest dedicated server lifecycle helpers."""

import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 556450
steam_anonymous_login_possible = True
DEFAULT_PORT = 27015
DEFAULT_QUERYPORT = 27016
DEFAULT_STEAMPORT = 8766
DEFAULT_MAXPLAYERS = 8
_SERVER_DATA_DIR = "server-data"
_CONFIG_FILE = "Server.cfg"
_SAVE_DIR = "saves"
_XVFB_SERVER_ARGS = "-screen 0 1024x768x24 -nolisten tcp"
_PORT_DEFINITIONS = tuple(
    {"key": key, "protocol": protocol}
    for key in ("port", "queryport", "steamport")
    for protocol in ("udp", "tcp")
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for The Forest server",
    "The directory to install The Forest in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update The Forest dedicated server to the latest version.",
    "Restart The Forest dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = (
    "port",
    "queryport",
    "steamport",
    "servername",
    "maxplayers",
)


def configure(server, ask, port=None, dir=None, *, exe_name="TheForestDedicatedServer.exe"):
    """Collect and store configuration values for The Forest server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": str(DEFAULT_QUERYPORT),
            "steamport": str(DEFAULT_STEAMPORT),
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": str(DEFAULT_MAXPLAYERS),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=[_SERVER_DATA_DIR],
        targets=[_SERVER_DATA_DIR],
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
        prompt="Where would you like to install The Forest server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _server_data_path(server, *parts):
    """Return a path inside the managed Forest data directory."""

    return os.path.join(server.data["dir"], _SERVER_DATA_DIR, *parts)


def sync_server_config(server):
    """Write the native Forest config and create its save directory."""

    config_path = _server_data_path(server, _CONFIG_FILE)
    save_path = _server_data_path(server, _SAVE_DIR)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    os.makedirs(save_path, exist_ok=True)
    config_lines = (
        "serverIP 0.0.0.0:{port}",
        "serverSteamPort {steamport}",
        "serverGamePort {port}",
        "serverQueryPort {queryport}",
        "serverName {servername}",
        "serverPlayers {maxplayers}",
        "serverPassword",
        "serverPasswordAdmin",
        "serverSteamAccount",
        "enableVAC off",
        "serverAutoSaveInterval 15",
        "difficulty Normal",
        "initType Continue",
        "slot 1",
        "showLogs on",
        "veganMode off",
        "vegetarianMode off",
        "resetHolesMode off",
        "treeRegrowMode on",
        "allowBuildingDestruction on",
        "allowEnemiesCreativeMode off",
        "allowCheats off",
    )
    values = {
        "port": int(server.data.get("port", DEFAULT_PORT)),
        "queryport": int(server.data.get("queryport", DEFAULT_QUERYPORT)),
        "steamport": int(server.data.get("steamport", DEFAULT_STEAMPORT)),
        "servername": str(server.data.get("servername", server.name)),
        "maxplayers": int(server.data.get("maxplayers", DEFAULT_MAXPLAYERS)),
    }
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(line.format(**values) for line in config_lines))
        handle.write("\n")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download The Forest server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update The Forest server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart The Forest server."


def prestart(server):
    """Refresh native configuration before launching The Forest."""

    sync_server_config(server)


def get_query_address(server):
    """Return The Forest's Steam query endpoint."""

    return (
        runtime_module.resolve_query_host(server),
        int(server.data["queryport"]),
        "a2s",
    )


def get_info_address(server):
    """Return the same endpoint used by the query command."""

    return get_query_address(server)


def _wrap_linux_command(command, wineprefix=None):
    """Run the Unity server under the virtual display it requires."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
        prefer_proton=True,
    )
    wrapped = [
        token
        for token in wrapped
        if token not in ("DISPLAY=", "WINEDLLOVERRIDES=winex11.drv=")
    ]
    wrapped = proton.prepend_env_assignments(
        wrapped,
        SDL_VIDEODRIVER="x11",
        SDL_AUDIODRIVER="dummy",
        WINEDLLOVERRIDES="",
    )
    return [
        "xvfb-run",
        "-a",
        "--server-args=" + _XVFB_SERVER_ARGS,
        *wrapped,
    ]


def get_start_command(server):
    """Build the command used to launch The Forest server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        server.data["exe_name"],
        "-batchmode",
        "-nosteamclient",
        "-nographics",
        "-configfilepath",
        "./{}/{}".format(_SERVER_DATA_DIR, _CONFIG_FILE),
        "-savefolderpath",
        "./{}/{}".format(_SERVER_DATA_DIR, _SAVE_DIR),
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop The Forest using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed The Forest status is not implemented yet."""


def message(server, msg):
    """The Forest has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for The Forest server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported The Forest datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "steamport", "maxplayers"),
        str_keys=("servername", "exe_name", "dir"),
    )


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=_PORT_DEFINITIONS,
    prefer_proton=True,
    extra_env={"ALPHAGSM_XVFB": "1"},
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=_PORT_DEFINITIONS,
    prefer_proton=True,
    extra_env={"ALPHAGSM_XVFB": "1"},
)
