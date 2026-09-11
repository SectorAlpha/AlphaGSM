"""DeadPoly dedicated server lifecycle helpers."""

import os
import shutil

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.platform_info import IS_LINUX
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2208380
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the DeadPoly server",
    "The directory to install DeadPoly in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the DeadPoly dedicated server to the latest version.",
    "Restart the DeadPoly dedicated server.",
)
command_functions = {}
max_stop_wait = 1
DEFAULT_EXECUTABLES = (
    "DeadPolyServer.exe",
    "DeadPoly/Binaries/Win64/DeadPolyServer.exe",
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
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="The maximum number of players.",
        value_type="integer",
        apply_to=("datastore", "launch_args", "native_config"),
        launch_arg_format="-maxplayers={value}",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised server name.",
        apply_to=("datastore", "native_config"),
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


def configure(server, ask, port=None, dir=None, *, exe_name="DeadPolyServer.exe"):
    """Collect and store configuration values for a DeadPoly server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "7778",
            "maxplayers": "100",
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DeadPoly/Saved", "DeadPoly/Saved/Config"],
        targets=["DeadPoly/Saved", "DeadPoly/Saved/Config"],
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
        prompt="Where would you like to install the DeadPoly server:",
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


def _seed_config_root(server):
    """Return the shipped DeadPoly config seed root."""

    return os.path.join(server.data["dir"], "DeadPoly", "Saved", "1 RENAME Config")


def _config_root(server):
    """Return the managed DeadPoly config root."""

    return os.path.join(server.data["dir"], "DeadPoly", "Saved", "Config")


def _game_ini_path(server):
    """Return the managed DeadPoly Game.ini path."""

    return os.path.join(_config_root(server), "WindowsServer", "Game.ini")


def _stage_config_tree(server):
    """Stage the shipped DeadPoly config tree into its runtime location."""

    config_root = _config_root(server)
    if os.path.isdir(config_root):
        return
    seed_root = _seed_config_root(server)
    if os.path.isdir(seed_root):
        shutil.copytree(seed_root, config_root)


def sync_server_config(server):
    """Keep the managed DeadPoly Game.ini aligned with AlphaGSM data."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return

    _stage_config_tree(server)
    config_path = _game_ini_path(server)
    if not os.path.isfile(config_path):
        return

    rewrite_equals_config(
        config_path,
        {
            "ServerName": str(server.data.get("servername") or ("AlphaGSM %s" % (server.name,))),
            "PlayerSlots": int(server.data.get("maxplayers") or 100),
        },
    )


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the DeadPoly server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)

restart = gamemodule_common.make_restart_hook()


def prestart(server):
    """Stage DeadPoly runtime config before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for DeadPoly."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "tcp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for DeadPoly."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a DeadPoly dedicated server."""

    executable = _resolve_executable_name(server)
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    cmd = [
        executable,
        "-log",
        "-nosteam",
        *dynamic_args,
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop DeadPoly using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed DeadPoly status is not implemented yet."""


def message(server, msg):
    """DeadPoly has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a DeadPoly server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported DeadPoly datastore edits."""

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
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)
