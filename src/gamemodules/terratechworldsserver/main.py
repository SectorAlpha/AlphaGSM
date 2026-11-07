"""TerraTech Worlds dedicated server lifecycle helpers."""

import json
import os
import shutil

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2533070
steam_anonymous_login_possible = True
_SHIPPING_EXE = os.path.join("TT2", "Binaries", "Win64", "TT2Server-Win64-Shipping.exe")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the TerraTech Worlds server",
    "The directory to install TerraTech Worlds in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the TerraTech Worlds dedicated server to the latest version.",
    "Restart the TerraTech Worlds dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def configure(server, ask, port=None, dir=None, *, exe_name="TT2Server.exe"):
    """Collect and store configuration values for a TerraTech Worlds server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["dedicated_server_config.json", "Saved"],
        targets=["dedicated_server_config.json", "Saved"],
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
        prompt="Where would you like to install the TerraTech Worlds server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _server_config_path(server):
    """Return the dedicated server config path."""

    return os.path.join(server.data["dir"], "dedicated_server_config.json")


def sync_server_config(server):
    """Keep the dedicated server config aligned with AlphaGSM datastore values."""

    config_path = _server_config_path(server)
    if not os.path.isfile(config_path):
        return
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)
    config["Port"] = int(server.data.get("port", 7777))
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
        fh.write("\n")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the TerraTech Worlds server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the TerraTech Worlds server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the TerraTech Worlds server."


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows server command for headless Linux hosts."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
    )
    wrapped = proton.prepend_env_assignments(
        wrapped,
        LIBGL_ALWAYS_SOFTWARE="1",
    )
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


def _resolve_start_executable(server):
    """Return the executable path to launch for the current host."""

    exe_name = server.data["exe_name"]
    if IS_LINUX and os.path.normpath(exe_name) == "TT2Server.exe":
        shipping_path = os.path.join(server.data["dir"], _SHIPPING_EXE)
        if os.path.isfile(shipping_path):
            return _SHIPPING_EXE
    return exe_name


def get_query_address(server):
    """TerraTech Worlds exposes its dedicated listener as a generic UDP port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the same UDP endpoint used by query()."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a TerraTech Worlds server."""

    exe_name = _resolve_start_executable(server)
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [exe_name, "-log"]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


def prestart(server):
    """Refresh the dedicated server config before each launch."""

    sync_server_config(server)


def do_stop(server, j):
    """Stop TerraTech Worlds using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed TerraTech Worlds status is not implemented yet."""


def message(server, msg):
    """TerraTech Worlds has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a TerraTech Worlds server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported TerraTech Worlds datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("exe_name", "dir"),
    )


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
)
