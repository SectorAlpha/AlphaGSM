"""Core Keeper dedicated server lifecycle helpers."""

import os
import re

import screen
import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1963720
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Core Keeper in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Core Keeper dedicated server to the latest version.",
    "Restart the Core Keeper dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def _patch_launch_script(server):
    launch_path = os.path.join(server.data["dir"], "_launch.sh")
    if not os.path.isfile(launch_path):
        return
    original = open(launch_path, encoding="utf-8", errors="replace").read()
    new = (
        "    xvfb-run -a --server-args=\"-screen 0 1x1x24 -nolisten tcp\" \\\n"
        "        env SDL_VIDEODRIVER=x11 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1 \\\n"
        "        LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH:$installdir/linux64/\" \\\n"
        "        \"$exepath\" -batchmode -logfile CoreKeeperServerLog.txt \"$@\" &\n"
    )
    pattern = re.compile(
        r"^\s*set -m\n\n"
        r"\s*rm -f /tmp/\.X99-lock\n\n"
        r"\s*Xvfb :99 -screen 0 1x1x24 -nolisten tcp &\n"
        r"\s*xvfbpid=\$!\n\n"
        r"\s*DISPLAY=:99 LD_LIBRARY_PATH=\"\$LD_LIBRARY_PATH:\$installdir/linux64/\" \\\n"
        r"\s*\"\$exepath\" -batchmode -logfile CoreKeeperServerLog.txt \"\$@\" &\n",
        re.MULTILINE,
    )
    updated, count = pattern.subn(new, original, count=1)
    if count == 0:
        return
    with open(launch_path, "w", encoding="utf-8") as handle:
        handle.write(updated)


def configure(server, ask, port=None, dir=None, *, exe_name="CoreKeeperServer"):
    """Collect and store configuration values for a Core Keeper server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "world": server.name,
            "worldindex": "0",
            "maxplayers": "8",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DedicatedServer", "GameInfo.txt", "GameID.txt"],
        targets=["DedicatedServer", "GameInfo.txt", "GameID.txt"],
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
        prompt="Where would you like to install the Core Keeper server:",
    )
    gamemodule_common.configure_executable(server, exe_name="_launch.sh")
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_patch_launch_script,
)
install.__doc__ = "Download the Core Keeper server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_patch_launch_script,
)
update.__doc__ = "Update the Core Keeper server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Core Keeper dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-world",
            str(server.data["worldindex"]),
            "-worldname",
            server.data["world"],
            "-port",
            str(server.data["port"]),
            "-maxplayers",
            str(server.data["maxplayers"]),
            "-datapath",
            os.path.join(server.data["dir"], "DedicatedServer"),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the UDP endpoint used for Core Keeper reachability checks."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the UDP endpoint used for Core Keeper info output."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Core Keeper by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Core Keeper status is not implemented yet."""


def message(server, msg):
    """Core Keeper has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Core Keeper server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Core Keeper datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers", "worldindex"),
        str_keys=("world", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
