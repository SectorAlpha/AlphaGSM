"""Conan Exiles dedicated server lifecycle helpers."""

import configparser
import os
import shutil

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 443030
steam_anonymous_login_possible = True
NATIVE_EXECUTABLE = (
    "ConanSandbox/Binaries/Linux/ConanSandboxServer-Linux-Shipping"
)
DEFAULT_EXECUTABLES = (
    NATIVE_EXECUTABLE,
    "ConanSandboxServer.sh",
)
LEGACY_WINDOWS_EXECUTABLES = (
    "ConanSandbox/Binaries/Win64/ConanSandboxServer-Win64-Shipping.exe",
    "ConanSandboxServer.exe",
)
config_sync_keys = ("port", "queryport", "maxplayers", "servername")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Conan Exiles server",
    "The directory to install Conan Exiles in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Conan Exiles dedicated server to the latest version.",
    "Restart the Conan Exiles dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "map": SettingSpec(
        canonical_key="map",
        description="The map to load when the Conan Exiles server starts.",
    ),
    "port": SettingSpec(
        canonical_key="port",
        description="The main Conan Exiles game port.",
        value_type="integer",
        apply_to=("datastore", "launch_args", "native_config"),
        launch_arg_format="-Port={value}",
    ),
    "queryport": SettingSpec(
        canonical_key="queryport",
        description="The Conan Exiles dedicated query port.",
        value_type="integer",
        apply_to=("datastore", "launch_args", "native_config"),
        launch_arg_format="-QueryPort={value}",
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
        description="The advertised Conan Exiles server name.",
        apply_to=("datastore", "native_config"),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name=NATIVE_EXECUTABLE,
):
    """Collect and store configuration values for a Conan Exiles server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "map": "ConanSandbox",
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": "40",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ConanSandbox/Saved", "ConanSandbox/Saved/Config"],
        targets=["ConanSandbox/Saved", "ConanSandbox/Saved/Config"],
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
        prompt="Where would you like to install the Conan Exiles server:",
    )
    if server.data.get("exe_name") in LEGACY_WINDOWS_EXECUTABLES:
        server.data["exe_name"] = exe_name
    else:
        gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _resolve_executable_name(server):
    """Return the real executable from the installed native Linux payload."""

    configured = server.data.get("exe_name")
    candidates = []
    if configured and configured not in LEGACY_WINDOWS_EXECUTABLES:
        candidates.append(configured)
    candidates.extend(name for name in DEFAULT_EXECUTABLES if name not in candidates)

    for candidate in candidates:
        if os.path.isfile(os.path.join(server.data["dir"], candidate)):
            return candidate
    raise ServerError("Executable file not found")


def _settings_dir(server):
    return os.path.join(server.data["dir"], "ConanSandbox", "Saved", "Config", "LinuxServer")


def _migrate_native_layout(server):
    """Preserve legacy Wine settings and saves when selecting the native payload."""

    saved_dir = os.path.join(server.data["dir"], "ConanSandbox", "Saved")
    legacy_settings_dir = os.path.join(saved_dir, "Config", "WindowsServer")
    settings_dir = _settings_dir(server)
    if os.path.isdir(legacy_settings_dir):
        os.makedirs(settings_dir, exist_ok=True)
        for filename in ("Engine.ini", "Game.ini", "ServerSettings.ini"):
            source = os.path.join(legacy_settings_dir, filename)
            destination = os.path.join(settings_dir, filename)
            if os.path.isfile(source) and not os.path.exists(destination):
                shutil.copy2(source, destination)

    legacy_database = os.path.join(saved_dir, "Game.db")
    native_database = os.path.join(saved_dir, "game.db")
    if os.path.isfile(legacy_database) and not os.path.exists(native_database):
        os.replace(legacy_database, native_database)

    if server.data.get("exe_name") in LEGACY_WINDOWS_EXECUTABLES:
        server.data["exe_name"] = NATIVE_EXECUTABLE
        save = getattr(server.data, "save", None)
        if callable(save):
            save()


def _engine_ini_path(server):
    return os.path.join(_settings_dir(server), "Engine.ini")


def _game_ini_path(server):
    return os.path.join(_settings_dir(server), "Game.ini")


def _server_settings_ini_path(server):
    return os.path.join(_settings_dir(server), "ServerSettings.ini")


def _template_path(filename):
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "docs",
            "server-templates",
            "conanexiles",
            filename,
        )
    )


def _load_ini(config_path, template_filename):
    parser = configparser.RawConfigParser(interpolation=None, strict=False)
    parser.optionxform = str
    source = config_path if os.path.isfile(config_path) else _template_path(template_filename)
    parser.read(source, encoding="utf-8")
    return parser


def sync_server_config(server):
    """Keep Conan Exiles config files aligned with AlphaGSM settings."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return

    _migrate_native_layout(server)
    settings_dir = _settings_dir(server)
    os.makedirs(settings_dir, exist_ok=True)

    engine = _load_ini(_engine_ini_path(server), "Engine.ini")
    if not engine.has_section("URL"):
        engine.add_section("URL")
    if not engine.has_section("OnlineSubsystem"):
        engine.add_section("OnlineSubsystem")
    if not engine.has_section("OnlineSubsystemNull"):
        engine.add_section("OnlineSubsystemNull")
    engine.set("URL", "Port", str(server.data.get("port", 7777)))
    engine.set(
        "OnlineSubsystemNull",
        "GameServerQueryPort",
        str(server.data.get("queryport", 27015)),
    )
    engine.set(
        "OnlineSubsystem",
        "ServerName",
        str(server.data.get("servername") or ("AlphaGSM %s" % (server.name,))),
    )
    if not engine.has_option("OnlineSubsystem", "ServerPassword"):
        engine.set("OnlineSubsystem", "ServerPassword", "")
    with open(_engine_ini_path(server), "w", encoding="utf-8") as handle:
        engine.write(handle, space_around_delimiters=False)

    game = _load_ini(_game_ini_path(server), "Game.ini")
    if not game.has_section("/Script/Engine.GameSession"):
        game.add_section("/Script/Engine.GameSession")
    game.set(
        "/Script/Engine.GameSession",
        "MaxPlayers",
        str(server.data.get("maxplayers", 40)),
    )
    with open(_game_ini_path(server), "w", encoding="utf-8") as handle:
        game.write(handle, space_around_delimiters=False)

    server_settings_path = _server_settings_ini_path(server)
    if not os.path.isfile(server_settings_path):
        server_settings = _load_ini(server_settings_path, "ServerSettings.ini")
        with open(server_settings_path, "w", encoding="utf-8") as handle:
            server_settings.write(handle, space_around_delimiters=False)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_platform": "linux"},
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Conan Exiles server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_platform": "linux"},
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Conan Exiles server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Conan Exiles server."


def prestart(server):
    """Refresh the managed Conan Exiles config files before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Conan Exiles serves A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Conan Exiles dedicated server."""

    executable = _resolve_executable_name(server)
    cmd = ["./" + executable]
    if server.data.get("map"):
        cmd.append(str(server.data["map"]))
    cmd.extend(
        [
            "-log",
            "-console",
            "-Port={}".format(server.data.get("port", 7777)),
            "-QueryPort={}".format(server.data.get("queryport", 27015)),
            "-MaxPlayers={}".format(server.data.get("maxplayers", 40)),
        ]
    )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Conan Exiles using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Conan Exiles status is not implemented yet."""


def message(server, msg):
    """Conan Exiles has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Conan Exiles server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Conan Exiles datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "maxplayers"),
        resolved_str_keys=("map", "servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )


_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "offset": 1, "protocol": "udp"},
    {"key": "queryport", "protocol": "udp"},
)
port_claim_definitions = _PORT_DEFINITIONS
ignored_port_keys = ("pingerport",)
_RUNTIME_EXTRA = {"run_as_host_user": True, "container_home": "/home/alphagsm"}


def get_runtime_requirements(server):
    """Return the native Linux server's runtime and complete UDP port set."""

    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=_PORT_DEFINITIONS,
        extra=_RUNTIME_EXTRA,
    )


def get_container_spec(server):
    """Build the native Linux container launch specification."""

    return runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=_PORT_DEFINITIONS,
        stdin_open=True,
        extra=_RUNTIME_EXTRA,
    )
