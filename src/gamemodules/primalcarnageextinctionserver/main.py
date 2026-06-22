"""Primal Carnage: Extinction dedicated server lifecycle helpers."""

import os
import shutil

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 336400
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Primal Carnage server",
    "The directory to install Primal Carnage in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Primal Carnage: Extinction dedicated server to the latest version.",
    "Restart the Primal Carnage: Extinction dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Win64/PrimalCarnageServer.exe"):
    """Collect and store configuration values for a Primal Carnage server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"queryport": "27015"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["PrimalCarnageGame/Config", "PrimalCarnageGame/Logs"],
        targets=["PrimalCarnageGame/Config", "PrimalCarnageGame/Logs"],
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
        prompt="Where would you like to install the Primal Carnage server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Primal Carnage server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Primal Carnage server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Primal Carnage server."


def _build_server_map_url(server):
    """Return the dedicated-server startup URL used by the UE3 server."""

    port = int(server.data.get("port", 7777))
    queryport = int(server.data.get("queryport", 27015))
    peerport = port + 1
    return (
        "PC-Docks"
        "?game=PrimalCarnageGame.PCTeamDeathMatchGame"
        f"?Port={port}"
        f"?PeerPort={peerport}"
        f"?QueryPort={queryport}"
        "?bIsDedicated=true"
    )


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows server command for headless Linux hosts."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
    )
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = [
        arg
        for arg in wrapped
        if not (
            arg.startswith("DISPLAY=")
            or arg.startswith("WINEDLLOVERRIDES=")
        )
    ]
    return ["xvfb-run", "-a", *wrapped]


def get_query_address(server):
    """Primal Carnage uses Steam A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Primal Carnage server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    binaries_dir = os.path.dirname(exe_path)
    cmd = [
        os.path.basename(server.data["exe_name"]),
        # This dedicated executable already enters server mode; passing a
        # literal "SERVER" token makes UE3 try to load a missing package.
        _build_server_map_url(server),
        "-seekfreeloadingserver",
        "-log",
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, binaries_dir


def do_stop(server, j):
    """Stop Primal Carnage using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Primal Carnage status is not implemented yet."""


def message(server, msg):
    """Primal Carnage has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Primal Carnage server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Primal Carnage datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
