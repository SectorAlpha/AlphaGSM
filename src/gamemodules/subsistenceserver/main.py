"""Subsistence dedicated server lifecycle helpers."""

import os
import shutil
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.simple_kv_config import rewrite_equals_config

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
config_sync_keys = ("queryport", "maxplayers", "servername", "serverpassword")


def _container_runtime_env(_server):
    """Return Docker runtime env for the shared wine-proton entrypoint."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 640x480x24 -ac",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "mshtml=",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }


def _container_start_command(server):
    """Return the Docker start tuple without host-side xvfb/wine wrappers."""

    command, cwd = get_start_command(server)
    command = proton.unwrap_runtime_command(command)
    if command[:2] == ["xvfb-run", "-a"]:
        command = command[2:]
    return command, cwd


def _udk_engine_config_path(server):
    return os.path.join(server.data["dir"], "UDKGame", "Config", "UDKEngine.ini")


def _default_engine_config_paths(server):
    config_dir = os.path.join(server.data["dir"], "UDKGame", "Config")
    return (
        os.path.join(config_dir, "DefaultEngine.ini"),
        os.path.join(config_dir, "DefaultEngineUDK.ini"),
        os.path.join(config_dir, "UDKEngine.ini"),
    )


def _dedicated_settings_path(server):
    return os.path.join(server.data["dir"], "UDKGame", "Config", "UDKDedServerSettings.ini")


def _dedicated_settings_paths(server):
    config_dir = os.path.join(server.data["dir"], "UDKGame", "Config")
    return (
        os.path.join(config_dir, "DefaultDedServerSettings.ini"),
        os.path.join(config_dir, "UDKDedServerSettings.ini"),
    )


def sync_server_config(server):
    """Keep the real UDK config files aligned with AlphaGSM settings."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return
    os.makedirs(os.path.join(server_dir, "UDKGame", "Config"), exist_ok=True)

    engine_values = {
        "QueryPort": int(server.data.get("queryport", 27016)),
    }
    settings_values = {
        "MaxPlayers": int(server.data.get("maxplayers", 10)),
        "ServerName": str(server.data.get("servername") or ("AlphaGSM %s" % (server.name,))),
        "Password": str(server.data.get("serverpassword", "")),
    }

    for config_path in _default_engine_config_paths(server):
        rewrite_equals_config(config_path, engine_values)
    for config_path in _dedicated_settings_paths(server):
        rewrite_equals_config(config_path, settings_values)


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Win64/UDK.exe"):
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
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Subsistence server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Subsistence server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Subsistence server."


def prestart(server):
    """Refresh the UDK config files before launch."""

    sync_server_config(server)


def get_start_command(server):
    """Build the command used to launch a Subsistence dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    port = server.data.get("port", 27015)
    queryport = server.data.get("queryport", 27016)
    maxplayers = server.data.get("maxplayers", 10)
    binaries_dir = server.data["dir"]
    # The dedicated server responds on the upstream UDK launcher, not the
    # bundled Subsistence.exe wrapper. Keep the UDKGame.log path enabled via
    # -log and pass the ports as explicit UDK flags instead of an inlined map
    # URL so the Win64 launcher follows the same contract as the working
    # Linux/Wine repro.
    cmd = [
        server.data["exe_name"],
        "server",
        "coldmap1?steamsockets",
        "-log",
        f"-Port={port}",
        f"-QueryPort={queryport}",
        f"-MaxPlayers={maxplayers}",
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
        cmd = proton.prepend_env_assignments(
            cmd,
            SDL_VIDEODRIVER="x11",
            SDL_AUDIODRIVER="dummy",
            WINEDLLOVERRIDES="mshtml=",
            LIBGL_ALWAYS_SOFTWARE="1",
        )
        if shutil.which("xvfb-run") is not None:
            cmd = [
                arg
                for arg in cmd
                if not (
                    arg.startswith("DISPLAY=")
                    or arg == "WINEDLLOVERRIDES=winex11.drv="
                )
            ]
            cmd = ["xvfb-run", "-a", *cmd]
    return cmd, binaries_dir


def get_query_address(server):
    """Return the Steam query endpoint for Subsistence."""

    return (
        runtime_module.resolve_query_host(server),
        int(server.data["queryport"]),
        "a2s",
    )


def get_info_address(server):
    """Return the info endpoint for Subsistence."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Subsistence using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


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
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "port", "protocol": "udp"},
    ),
    extra_env=_container_runtime_env,
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)


def get_container_spec(server):
    """Return the Docker launch spec for the shared wine-proton runtime."""

    return proton.get_container_spec(
        server,
        _container_start_command,
        port_definitions=(
            {"key": "queryport", "protocol": "udp"},
            {"key": "port", "protocol": "udp"},
        ),
        extra_env=_container_runtime_env(server),
    )
