"""Wreckfest dedicated server lifecycle helpers."""

import os
import shutil
import re

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from utils.platform_info import IS_LINUX
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from server.modsupport.native_workshop import build_native_workshop_support, safe_server_path
from .workshop import WORKSHOP_APP_ID, apply_workshop

steam_app_id = 361580
steam_anonymous_login_possible = True
workshop_app_id = WORKSHOP_APP_ID
MOD_SUPPORT = build_native_workshop_support(
    game_label="Wreckfest", workshop_app_id=workshop_app_id, apply_callback=apply_workshop,
)
CLIENT_STEAM_APP_ID = 228380
DEFAULT_EXECUTABLES = ("Wreckfest_x64.exe", "Wreckfest.exe")
DEFAULT_CONFIGFILE = "server_config.cfg"
INITIAL_CONFIGFILE = "initial_server_config.cfg"

commands = ("update", "restart") + MOD_SUPPORT.commands
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Wreckfest server",
    "The directory to install Wreckfest in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Wreckfest dedicated server to the latest version.",
    "Restart the Wreckfest dedicated server.",
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions = dict(MOD_SUPPORT.command_functions)
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "steamport", "servername", "serverpassword", "maxplayers", "track")
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
    "track": SettingSpec(
        canonical_key="track",
        description="Installed native event identifier, including enabled Workshop tracks.",
        apply_to=("datastore", "native_config"),
        native_config_key="track",
    ),
    "wineprefix": SettingSpec(
        canonical_key="wineprefix",
        description="Wine or Proton prefix directory for the configured runtime.",
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
    MOD_SUPPORT.ensure_mod_state(server)
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
    return str(safe_server_path(server, server.data.get("configfile", DEFAULT_CONFIGFILE)))


def _ensure_server_config(server):
    """Seed server_config.cfg from the vendor example when missing."""

    config_path = _config_path(server)
    if os.path.isfile(config_path):
        return config_path

    initial_config = str(safe_server_path(server, INITIAL_CONFIGFILE))
    if os.path.isfile(initial_config):
        shutil.copyfile(initial_config, config_path)
        return config_path

    shutil.copyfile(_template_path(), config_path)
    return config_path


def _ensure_steam_appid(server):
    """Keep the parent game app id available for the dedicated launcher."""

    appid_path = str(safe_server_path(server, "steam_appid.txt"))
    if os.path.isfile(appid_path):
        return
    with open(appid_path, "w", encoding="utf-8") as handle:
        handle.write(f"{CLIENT_STEAM_APP_ID}\n")


def sync_server_config(server):
    """Keep the Wreckfest config aligned with AlphaGSM settings."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return
    if "track" in server.data:
        _validate_track(server, server.data["track"])

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
    apply_automatic_mods(server)


def apply_automatic_mods(server):
    """Respect autoapply during install, update and start, including disablement."""
    if MOD_SUPPORT.ensure_mod_state(server)["autoapply"]:
        MOD_SUPPORT.apply_configured_mods(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
    post_download_hook=apply_automatic_mods,
)
update.__doc__ = "Update the Wreckfest server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Wreckfest server."


def get_query_address(server):
    """Return Linux UDP reachability or the historical native-host A2S endpoint.

    Linux probes the observed native GNS listener on the configured query port.
    UDP silence counts as reachable; the elapsed probe time is not an RTT and
    provides no game metadata. Engine startup must be checked separately.
    """

    host = runtime_module.resolve_query_host(server)
    if IS_LINUX:
        return (host, int(server.data["queryport"]), "udp")
    return (host, int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the info endpoint used by Wreckfest."""

    return get_query_address(server)


def _native_start_command(server):
    """Build the Windows command independently of host Wine availability."""

    exe_name = _resolve_executable_name(server)
    _ensure_server_config(server)
    _ensure_steam_appid(server)
    cmd = [
        exe_name,
        "-s",
        "server_config=%s" % (server.data.get("configfile", DEFAULT_CONFIGFILE),),
    ]
    if IS_LINUX:
        if not all(re.fullmatch(r"[A-Za-z0-9_. /=-]+", token) for token in cmd):
            raise ServerError("Wreckfest console launch does not support shell metacharacters")
        cmd = ["cmd.exe", "/c", *cmd]
    return cmd, server.data["dir"]


def get_start_command(server):
    """Launch the native console on a captured terminal rather than a pipe."""
    command, directory = _native_start_command(server)
    if IS_LINUX:
        command = proton.wrap_console_command(_wrap_linux_command(command, server.data.get("wineprefix")))
    return command, directory


def _wrap_linux_command(command, wineprefix=None):
    """Use the same X11 drivers as the Windows container runtime."""
    wrapped = proton.wrap_command(command, wineprefix=wineprefix, prefer_proton=True)
    wrapper = wrapped[:-len(command)]
    wrapped = [argument for argument in wrapper if not argument.startswith(
        ("DISPLAY=", "WINEDLLOVERRIDES="))] + list(command)
    wrapped = proton.prepend_env_assignments(
        wrapped, WINEDLLOVERRIDES="", SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy",
    )
    return ["xvfb-run", "-a",
            "--server-args=-screen 0 1024x768x24 -nolisten tcp", *wrapped]


def prestart(server):
    """Refresh the managed config before launch."""

    _ensure_steam_appid(server)
    sync_server_config(server)
    apply_automatic_mods(server)


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
        resolved_str_keys=("configfile", "servername", "serverpassword", "exe_name", "dir", "wineprefix"),
        resolved_handlers={"track": _validate_track},
        backup_module=backup_utils,
    )


def _validate_track(server, *values):
    """Only select native events present in the installation or local mods."""
    value = str(values[0]) if values else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise ServerError("Wreckfest track must be a native event identifier")
    for relative in ("data/property/event", "mods"):
        base = safe_server_path(server, relative)
        for event in base.rglob(value + ".evse"):
            safe_server_path(server, event.relative_to(server.data["dir"]))
            if event.is_file():
                return value
    raise ServerError("Wreckfest track is not installed; apply its Workshop mod first")


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
    extra_host_dependencies=(proton.xvfb_host_dependency(), proton.console_host_dependency()),
    stop_mode="exec-console",
    stdin_open=True,
)


_build_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=_native_start_command,
    port_definitions=(
        {"key": "steamport", "protocol": "udp"},
        {"key": "steamport", "protocol": "tcp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
    stop_mode="exec-console",
    stdin_open=True,
)


def get_container_spec(server):
    """Give Wine a PTY while retaining the managed FIFO for console input.

    The image entrypoint execs script before bootstrapping Wine. The inner
    entrypoint then starts Xvfb and Wine once, with the newly allocated PTY.
    """
    spec = _build_container_spec(server)
    spec["command"] = proton.wrap_console_command([
        "/usr/local/bin/alphagsm-wine-proton-entrypoint", *spec["command"],
    ])
    return spec
