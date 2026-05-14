"""Subsistence dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1362640
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Subsistence server",
    "The directory to install Subsistence in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Subsistence dedicated server to the latest version.",
    "Restart the Subsistence dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Win32/Subsistence.exe"):
    """Collect and store configuration values for a Subsistence server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27016",
            "maxplayers": "10",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ServerData", "Binaries/Win32"],
        targets=["ServerData"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Subsistence server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Subsistence server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Subsistence server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Subsistence server."


def get_start_command(server):
    """Build the command used to launch a Subsistence dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    # The bat file shipped with the server uses 'start /B Subsistence.exe server coldmap1'
    # which fails under Wine (ShellExecuteEx not supported).  We run Subsistence.exe
    # directly with the same UDK URL arguments inlined into the map string.
    port = server.data.get("port", 27015)
    queryport = server.data.get("queryport", 27016)
    maxplayers = server.data.get("maxplayers", 10)
    map_url = (
        f"server coldmap1?Port={port}?QueryPort={queryport}"
        f"?MaxPlayers={maxplayers}?steamsockets"
    )
    # Work from the exe's own directory so DLL loading succeeds.
    # Use the basename only (no path prefix) because cwd is already the exe dir.
    binaries_dir = os.path.join(server.data["dir"], "Binaries", "Win32")
    # -log writes UE3 engine output to UDKGame/Logs/Launch.log instead of a
    # Window owned by the process.  LIBGL_ALWAYS_SOFTWARE forces Mesa software
    # rendering so that wined3d SM3 shader compilation never hits GPU driver
    # issues that crash UE3 combined client/server binaries under Wine.
    cmd = ["Subsistence.exe", map_url, "-log"]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
        cmd = proton.prepend_env_assignments(cmd, LIBGL_ALWAYS_SOFTWARE="1")
    return cmd, binaries_dir


def do_stop(server, j):
    """Stop Subsistence using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Subsistence status is not implemented yet."""


def message(server, msg):
    """Subsistence has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Subsistence server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Subsistence datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
