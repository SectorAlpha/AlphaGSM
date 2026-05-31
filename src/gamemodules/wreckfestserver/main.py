"""Wreckfest dedicated server lifecycle helpers."""

import os
import shutil

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from utils.platform_info import IS_LINUX
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module

steam_app_id = 361580
steam_anonymous_login_possible = True
CLIENT_STEAM_APP_ID = 228380
DEFAULT_EXECUTABLES = ("Wreckfest_x64.exe", "Wreckfest.exe")
DEFAULT_CONFIGFILE = "server_config.cfg"
INITIAL_CONFIGFILE = "initial_server_config.cfg"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Wreckfest server",
    "The directory to install Wreckfest in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Wreckfest dedicated server to the latest version.",
    "Restart the Wreckfest dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "steamport", "servername", "serverpassword", "maxplayers")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The main game port for the Wreckfest server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="game_port",
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        description="The Steam query port for the Wreckfest server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="query_port",
    ),
    "steamport": SettingSpec(
        canonical_key="steamport",
        description="The Steam networking port for the Wreckfest server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="steam_port",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised Wreckfest server name.",
        apply_to=("datastore", "native_config"),
        native_config_key="server_name",
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required to join the Wreckfest server.",
        apply_to=("datastore", "native_config"),
        native_config_key="password",
        secret=True,
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="The maximum number of players allowed on the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="max_players",
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


def configure(server, ask, port=None, dir=None, *, exe_name="Wreckfest_x64.exe"):
    """Collect and store configuration values for a Wreckfest server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "configfile": DEFAULT_CONFIGFILE,
            "queryport": "27016",
            "steamport": "27015",
            "servername": "AlphaGSM %s" % (server.name,),
            "serverpassword": "",
            "maxplayers": "24",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=[DEFAULT_CONFIGFILE, "savegame", "log.txt"],
        targets=[DEFAULT_CONFIGFILE, "savegame", "log.txt"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=33540,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Wreckfest server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _resolve_executable_name(server):
    """Return the dedicated executable from the installed Wreckfest payload."""

    configured = server.data.get("exe_name")
    candidates = []
    if configured:
        candidates.append(configured)
    candidates.extend(name for name in DEFAULT_EXECUTABLES if name not in candidates)

    for candidate in candidates:
        if os.path.isfile(os.path.join(server.data["dir"], candidate)):
            return candidate
    raise ServerError("Executable file not found")


def _template_path():
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "docs",
            "server-templates",
            "wreckfestserver",
            DEFAULT_CONFIGFILE,
        )
    )


def _config_path(server):
    return os.path.join(
        server.data["dir"],
        server.data.get("configfile", DEFAULT_CONFIGFILE),
    )


def _ensure_server_config(server):
    """Seed server_config.cfg from the vendor example when missing."""

    config_path = _config_path(server)
    if os.path.isfile(config_path):
        return config_path

    initial_config = os.path.join(server.data["dir"], INITIAL_CONFIGFILE)
    if os.path.isfile(initial_config):
        shutil.copyfile(initial_config, config_path)
        return config_path

    shutil.copyfile(_template_path(), config_path)
    return config_path


def _ensure_steam_appid(server):
    """Keep the parent game app id available for the dedicated launcher."""

    appid_path = os.path.join(server.data["dir"], "steam_appid.txt")
    if os.path.isfile(appid_path):
        return
    with open(appid_path, "w", encoding="utf-8") as handle:
        handle.write(f"{CLIENT_STEAM_APP_ID}\n")


def sync_server_config(server):
    """Keep the Wreckfest config aligned with AlphaGSM settings."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return

    config_path = _ensure_server_config(server)
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "port": 33540,
            "queryport": 27016,
            "steamport": 27015,
            "servername": "AlphaGSM %s" % (server.name,),
            "serverpassword": "",
            "maxplayers": 24,
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            str(int(current_value))
            if spec.canonical_key in {"port", "queryport", "steamport", "maxplayers"}
            else str(current_value)
        ),
    )
    rewrite_equals_config(config_path, config_values)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
_base_install.__doc__ = "Download the Wreckfest server files via SteamCMD."


def install(server):
    """Download the Wreckfest server files via SteamCMD."""

    _base_install(server)
    _ensure_steam_appid(server)
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Wreckfest server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Wreckfest server."


def get_query_address(server):
    """Return the live Wreckfest query endpoint.

    On Linux, the Docker Wine/Proton lane currently exposes a stable generic
    TCP surface on the managed gameplay port, while the configured Steam query
    port does not answer A2S reliably. Keep the historical A2S mapping on
    non-Linux hosts.
    """

    host = runtime_module.resolve_query_host(server)
    if IS_LINUX:
        return (host, int(server.data["port"]), "tcp")
    return (host, int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the info endpoint used by Wreckfest."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Wreckfest dedicated server."""

    exe_name = _resolve_executable_name(server)
    _ensure_server_config(server)
    _ensure_steam_appid(server)
    cmd = [
        exe_name,
        "-s",
        "server_config=%s" % (server.data.get("configfile", DEFAULT_CONFIGFILE),),
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def prestart(server):
    """Refresh the managed config before launch."""

    _ensure_steam_appid(server)
    sync_server_config(server)


def do_stop(server, j):
    """Stop Wreckfest using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Wreckfest status is not implemented yet."""


def message(server, msg):
    """Wreckfest has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Wreckfest server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Wreckfest datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "steamport", "maxplayers"),
        resolved_str_keys=("configfile", "servername", "serverpassword", "exe_name", "dir"),
        backup_module=backup_utils,
    )


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(
        {"key": "steamport", "protocol": "udp"},
        {"key": "steamport", "protocol": "tcp"},
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
        {"key": "steamport", "protocol": "udp"},
        {"key": "steamport", "protocol": "tcp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)
