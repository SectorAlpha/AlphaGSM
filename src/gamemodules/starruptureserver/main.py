"""StarRupture dedicated server lifecycle helpers."""

import json
import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.backups import backups as backup_utils

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3809400
steam_anonymous_login_possible = True
config_sync_keys = ("servername", "maxplayers")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the StarRupture server",
    "The directory to install StarRupture in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the StarRupture dedicated server to the latest version.",
    "Restart the StarRupture dedicated server.",
)
command_functions = {}
max_stop_wait = 1
DEFAULT_EXECUTABLES = (
    "StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe",
    "StarRuptureServerEOS.exe",
)
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port for the server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-Port={value}",
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="The maximum number of players.",
        value_type="integer",
        apply_to=("datastore", "launch_args", "native_config"),
        launch_arg_format="-MaxPlayers={value}",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised server name.",
        apply_to=("datastore", "launch_args", "native_config"),
        launch_arg_format="-ServerName={value}",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


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


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe",
):
    """Collect and store configuration values for a StarRupture server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Config", "Saves", "Mods"],
        targets=["Config", "Saves", "Mods"],
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": "4",
        },
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
        prompt="Where would you like to install the StarRupture server:",
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


def _settings_path(server):
    """Return the managed DSSettings.txt path."""

    return os.path.join(server.data["dir"], "DSSettings.txt")


def _template_settings_path():
    """Return the checked-in DSSettings template path."""

    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "docs",
            "server-templates",
            "starruptureserver",
            "DSSettings.txt",
        )
    )


def _load_settings_payload(server):
    """Load the current or template DSSettings payload."""

    settings_path = _settings_path(server)
    source_path = settings_path if os.path.isfile(settings_path) else _template_settings_path()
    with open(source_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sync_server_config(server):
    """Keep DSSettings.txt aligned with AlphaGSM-managed settings."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return

    payload = _load_settings_payload(server)
    payload["SessionName"] = str(
        server.data.get("servername") or ("AlphaGSM %s" % (server.name,))
    )
    payload.setdefault("SaveGameInterval", "300")
    payload.setdefault("StartNewGame", "true")
    payload.setdefault("LoadSavedGame", "false")
    payload.setdefault("SaveGameName", "AutoSave0.sav")

    settings_path = _settings_path(server)
    os.makedirs(os.path.dirname(settings_path), exist_ok=True)
    with open(settings_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the StarRupture server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the StarRupture server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the StarRupture server."


def prestart(server):
    """Refresh DSSettings.txt before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for StarRupture."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for StarRupture."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a StarRupture dedicated server."""

    executable = _resolve_executable_name(server)
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    cmd = [
        executable,
        "-Log",
        "-MULTIHOME=0.0.0.0",
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
    """Stop StarRupture by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed StarRupture status is not implemented yet."""


def message(server, msg):
    """StarRupture has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a StarRupture server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported StarRupture datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("servername", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_env=_container_runtime_env,
)
