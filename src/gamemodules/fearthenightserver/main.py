"""Fear the Night dedicated server lifecycle helpers."""

import configparser
import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 764940
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Fear the Night server",
    "The directory to install Fear the Night in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Fear the Night dedicated server to the latest version.",
    "Restart the Fear the Night dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "maxplayers", "servername", "startmap")


def configure(server, ask, port=None, dir=None, *, exe_name="Moonlight/Binaries/Win64/MoonlightServer.exe"):
    """Collect and store configuration values for a Fear the Night server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "maxplayers": "40",
            "servername": "AlphaGSM %s" % (server.name,),
            "startmap": "Pittsburgh_Overworld",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Moonlight/Saved", "Moonlight/Config", "Moonlight/Binaries/Win64"],
        targets=["Moonlight/Saved", "Moonlight/Config"],
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
        prompt="Where would you like to install the Fear the Night server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _engine_ini_path(server):
    """Return the managed Fear the Night Engine.ini override path."""

    return os.path.join(
        server.data["dir"],
        "Moonlight",
        "Saved",
        "Config",
        "WindowsServer",
        "Engine.ini",
    )


def _game_user_settings_path(server):
    """Return the managed Fear the Night GameUserSettings.ini path."""

    return os.path.join(
        server.data["dir"],
        "Moonlight",
        "Saved",
        "Config",
        "WindowsServer",
        "GameUserSettings.ini",
    )


def _load_ini(path):
    """Return a permissive config parser for Unreal-style INI files."""

    parser = configparser.RawConfigParser(strict=False)
    parser.optionxform = str
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            parser.read_file(handle)
    return parser


def sync_server_config(server):
    """Keep Fear the Night's native config files aligned with AlphaGSM values."""

    if not server.data.get("dir"):
        return

    engine_ini_path = _engine_ini_path(server)
    os.makedirs(os.path.dirname(engine_ini_path), exist_ok=True)
    engine_ini = _load_ini(engine_ini_path)
    if not engine_ini.has_section("URL"):
        engine_ini.add_section("URL")
    engine_ini.set("URL", "Port", str(int(server.data.get("port", 7777))))
    engine_ini.set("URL", "PeerPort", str(int(server.data.get("port", 7777)) + 1))
    if not engine_ini.has_section("OnlineSubsystemSteam"):
        engine_ini.add_section("OnlineSubsystemSteam")
    engine_ini.set(
        "OnlineSubsystemSteam",
        "GameServerQueryPort",
        str(int(server.data.get("queryport", 27015))),
    )
    with open(engine_ini_path, "w", encoding="utf-8") as handle:
        engine_ini.write(handle)

    game_user_settings_path = _game_user_settings_path(server)
    game_user_settings = _load_ini(game_user_settings_path)
    if not game_user_settings.has_section("SessionSettings"):
        game_user_settings.add_section("SessionSettings")
    game_user_settings.set(
        "SessionSettings",
        "SessionName",
        str(server.data.get("servername", "AlphaGSM %s" % (server.name,))),
    )
    if not game_user_settings.has_section("/Script/Engine.GameSession"):
        game_user_settings.add_section("/Script/Engine.GameSession")
    game_user_settings.set(
        "/Script/Engine.GameSession",
        "MaxPlayers",
        str(int(server.data.get("maxplayers", 40))),
    )
    with open(game_user_settings_path, "w", encoding="utf-8") as handle:
        game_user_settings.write(handle)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Fear the Night server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def prestart(server):
    """Refresh Fear the Night's native config files before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the live Fear the Night query endpoint.

    On the current Linux/Wine-Proton lane, the dedicated server binds the
    managed game port as generic UDP but does not expose a working A2S listener
    on the configured Steam query port. Keep the historical A2S mapping on
    non-Linux hosts.
    """

    host = runtime_module.resolve_query_host(server)
    if IS_LINUX:
        return (host, int(server.data["port"]), "udp")
    return (host, int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Fear the Night server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    map_url = (
        f"{server.data['startmap']}?listen?Port={int(server.data.get('port', 7777))}"
        f"?QueryPort={int(server.data.get('queryport', 27015))}"
        f"?SessionName={server.data.get('servername', 'AlphaGSM %s' % (server.name,))}"
        f"?MaxPlayers={int(server.data.get('maxplayers', 40))}"
    )
    cmd = [server.data["exe_name"], map_url, "-game", "-server", "-log"]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Fear the Night using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Fear the Night status is not implemented yet."


def message(server, msg):
    """Fear the Night has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Fear the Night server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Fear the Night datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("servername", "startmap", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'udp'}),
)
