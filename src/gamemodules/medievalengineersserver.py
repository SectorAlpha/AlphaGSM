"""Medieval Engineers dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 367970
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Medieval Engineers server",
    "The directory to install Medieval Engineers in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Medieval Engineers dedicated server to the latest version.",
    "Restart the Medieval Engineers dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="DedicatedServer64/MedievalEngineersDedicated.exe"):
    """Collect and store configuration values for a Medieval Engineers server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DedicatedServer64", "Content", "global.cfg"],
        targets=["DedicatedServer64", "Content", "global.cfg"],
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
        prompt="Where would you like to install the Medieval Engineers server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Medieval Engineers server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Medieval Engineers server files and optionally restart the server."

restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Medieval Engineers server."


def get_start_command(server):
    """Build the command used to launch a Medieval Engineers dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"], "-console", "-port", str(server.data["port"])]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
        # ME uses Wine Mono whose Path.GetTempPath() reads the Unix TMPDIR env
        # var first.  If TMPDIR points to a path on an external mount, Wine's
        # drive mapping turns it into an inaccessible Windows path (e.g.
        # Q:\media\...\useme).  When TMPDIR is unset, Mono falls through to
        # InternalGetTempPath() → Wine's GetTempPath() → reads C:\users\...\Temp
        # which is always accessible.  Also unset TMP/TEMP so Wine can control
        # them without conflicting overrides.
        cmd = [
            "env",
            "-u", "TMPDIR",
            "-u", "TMP",
            "-u", "TEMP",
        ] + cmd
    return cmd, server.data["dir"]
def do_stop(server, j):
    """Stop Medieval Engineers using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


status = gamemodule_common.make_noop_status_hook()
status.__doc__ = "Detailed Medieval Engineers status is not implemented yet."


def message(server, msg):
    """Medieval Engineers has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Medieval Engineers server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Medieval Engineers datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
