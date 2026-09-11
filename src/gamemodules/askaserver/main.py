"""ASKA dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from utils.simple_kv_config import rewrite_spaced_equals_config

steam_app_id = 3246670
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ASKA server",
    "The directory to install ASKA in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the ASKA dedicated server to the latest version.",
    "Restart the ASKA dedicated server.",
)
command_functions = {}
config_sync_keys = (
    "port",
    "queryport",
    "servername",
    "displayname",
    "password",
    "authenticationtoken",
    "region",
)
setting_schema = {
    "password": SettingSpec(
        canonical_key="password",
        description="Password required to join the server.",
        secret=True,
    ),
    "authenticationtoken": SettingSpec(
        canonical_key="authenticationtoken",
        aliases=("gslt", "authentication_token"),
        description="Steam game-server login token generated for ASKA app 1898300.",
        secret=True,
    ),
    "region": SettingSpec(
        canonical_key="region",
        description="Steam matchmaking region used to list the server.",
    ),
}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="AskaServer.exe"):
    """Collect and store configuration values for an ASKA server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": server.name,
            "displayname": "AlphaGSM %s" % (server.name,),
            "password": "",
            "maxplayers": "4",
            "queryport": "27016",
            "authenticationtoken": "",
            "region": "default",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["SaveGames", "ServerConfig"],
        targets=["SaveGames", "ServerConfig"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ASKA server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
_base_install.__doc__ = "Download the ASKA server files via SteamCMD."


def _properties_path(server):
    return os.path.join(server.data["dir"], "server properties.txt")


def sync_server_config(server):
    """Write AlphaGSM settings to ASKA's current properties-file contract."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return
    properties_path = _properties_path(server)
    if not os.path.isfile(properties_path):
        return
    rewrite_spaced_equals_config(
        properties_path,
        {
            "display name": server.data["displayname"],
            "server name": server.data["servername"],
            "password": server.data.get("password", ""),
            "steam game port": int(server.data["port"]),
            "steam query port": int(server.data["queryport"]),
            "authentication token": server.data.get("authenticationtoken", ""),
            "region": server.data.get("region", "default"),
        },
    )


def install(server):
    """Download ASKA and restore managed properties overwritten by SteamCMD."""

    _base_install(server)
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)


restart = gamemodule_common.make_restart_hook()


def get_provider_requirements(server):
    """Declare ASKA's Steam game-server login token requirement."""

    return [
        {
            "provider": "steam",
            "kind": "token",
            "keys": ("authenticationtoken",),
            "required_for": ("start",),
            "support_category": "provider-token",
            "summary": "a Steam game-server login token generated for ASKA app 1898300",
            "actions": (
                "Generate a token for app 1898300 at Steam Game Server Account Management",
                "Set authenticationtoken to that token before starting ASKA",
            ),
            "docs_slug": "askaserver",
        }
    ]


def prestart(server):
    """Validate authentication and refresh the current ASKA properties file."""

    gamemodule_common.validate_provider_requirements(
        "askaserver",
        server,
        phase="start",
        requirements=get_provider_requirements(server),
    )
    sync_server_config(server)


def get_start_command(server):
    """Build the command used to launch an ASKA dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    gamemodule_common.validate_provider_requirements(
        "askaserver",
        server,
        phase="start",
        requirements=get_provider_requirements(server),
    )
    command = [
        server.data["exe_name"],
        "-batchmode",
        "-nographics",
        "-propertiesPath",
        "server properties.txt",
    ]
    if IS_LINUX:
        game_command = command
        command = proton.wrap_command(
            command,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
        # Unity still creates a window in batch mode under Wine.
        wrapper = command[:-len(game_command)]
        command = [arg for arg in wrapper if not arg.startswith(("DISPLAY=", "WINEDLLOVERRIDES="))] + game_command
        command = proton.prepend_env_assignments(
            command, WINEDLLOVERRIDES="", SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy",
        )
        command = ["xvfb-run", "-a", "--server-args=-screen 0 1024x768x24 -nolisten tcp", *command]
    return (command, server.data["dir"])


def get_query_address(server):
    """Return ASKA's configured Steam A2S endpoint."""

    return runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Use the configured Steam query endpoint for server information."""

    return get_query_address(server)


_DISPLAY_ENV = {
    "ALPHAGSM_XVFB": "1",
    "SDL_VIDEODRIVER": "x11",
    "SDL_AUDIODRIVER": "dummy",
    "WINEDLLOVERRIDES": "",
}


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    extra_env=_DISPLAY_ENV,
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
    port_definitions=(("port", "udp"), ("queryport", "udp")),
)
get_runtime_requirements.__doc__ = "Return Docker runtime metadata for Wine/Proton-backed servers."


get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    extra_env=_DISPLAY_ENV,
    get_start_command=get_start_command,
    port_definitions=(("port", "udp"), ("queryport", "udp")),
)
get_container_spec.__doc__ = "Return the Docker launch spec for ASKA."


def do_stop(server, j):
    """Stop the ASKA server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed ASKA status is not implemented yet."""


def message(server, msg):
    """ASKA has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ASKA server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ASKA datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("servername", "displayname", "password", "authenticationtoken", "region", "exe_name", "dir"),
    )
