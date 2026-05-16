"""Onset dedicated server lifecycle helpers."""

import json
import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1204170
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Onset server",
    "The directory to install Onset in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Onset dedicated server to the latest version.",
    "Restart the Onset dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = (
    "servername",
    "servername_short",
    "gamemode",
    "website_url",
    "ipaddress",
    "port",
    "maxplayers",
    "password",
    "timeout",
    "iplimit",
)
setting_schema = {
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised Onset server name.",
        apply_to=("datastore", "native_config"),
    ),
    "servername_short": SettingSpec(
        canonical_key="servername_short",
        description="The short server name used for rich presence.",
        apply_to=("datastore", "native_config"),
    ),
    "gamemode": SettingSpec(
        canonical_key="gamemode",
        description="The short description shown for the server.",
        apply_to=("datastore", "native_config"),
    ),
    "website_url": SettingSpec(
        canonical_key="website_url",
        description="The homepage URL advertised by the server.",
        apply_to=("datastore", "native_config"),
    ),
    "ipaddress": SettingSpec(
        canonical_key="ipaddress",
        description="The bind address written to server_config.json.",
        apply_to=("datastore", "native_config"),
    ),
    "port": SettingSpec(
        canonical_key="port",
        description="Primary gameplay port.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum players allowed on the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
    ),
    "password": SettingSpec(
        canonical_key="password",
        description="Optional join password.",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
    "timeout": SettingSpec(
        canonical_key="timeout",
        description="Client timeout in milliseconds.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
    ),
    "iplimit": SettingSpec(
        canonical_key="iplimit",
        description="Maximum simultaneous connections per IP.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _config_path(server):
    return os.path.join(server.data["dir"], "server_config.json")


def _query_port(server):
    return int(server.data["queryport"])


def _http_port(server):
    return int(server.data["httpport"])


def _sync_derived_ports(server):
    base_port = int(server.data["port"])
    server.data["queryport"] = base_port - 1
    server.data["httpport"] = base_port - 2


def sync_server_config(server):
    _sync_derived_ports(server)
    config = {
        "servername": str(server.data.get("servername", "AlphaGSM %s" % (server.name,))),
        "servername_short": str(server.data.get("servername_short", server.name)),
        "gamemode": str(server.data.get("gamemode", "Sandbox")),
        "website_url": str(server.data.get("website_url", "https://playonset.com")),
        "ipaddress": str(server.data.get("ipaddress", "0.0.0.0")),
        "port": int(server.data.get("port", 7777)),
        "maxplayers": int(server.data.get("maxplayers", 25)),
        "password": str(server.data.get("password", "")),
        "timeout": int(server.data.get("timeout", 15000)),
        "iplimit": int(server.data.get("iplimit", 5)),
        "vac": False,
        "masterlist": False,
        "plugins": [],
        "packages": ["sandbox"],
        "discord_client_id": "",
        "connect_screen_url": "loadingscreen.html",
        "connect_screen_show_cursor": True,
        "voice": True,
        "voice_sample_rate": 24000,
        "voice_spatialization": True,
        "sandbox": False,
        "dev_whitelist": False,
        "dev_whitelist_steamid": [],
    }
    with open(_config_path(server), "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=4)
        handle.write("\n")


def _finalize_install_layout(server):
    sync_server_config(server)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if os.path.isfile(exe_path):
        os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    server.data.save()


def configure(server, ask, port=None, dir=None, *, exe_name="start_linux.sh"):
    """Collect and store configuration values for an Onset server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "servername_short": server.name,
            "gamemode": "Sandbox",
            "website_url": "https://playonset.com",
            "ipaddress": "0.0.0.0",
            "maxplayers": 25,
            "password": "",
            "timeout": 15000,
            "iplimit": 5,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["server_config.json", "packages"],
        targets=["server_config.json", "packages"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    _sync_derived_ports(server)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Onset server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Onset server files via SteamCMD."""

    _base_install(server)
    _finalize_install_layout(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Onset server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Onset server."


def get_query_address(server):
    """Onset exposes Valve-style server queries on the documented query port."""

    return runtime_module.resolve_query_host(server), _query_port(server), "a2s"


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch an Onset dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    sync_server_config(server)
    return (
        [
            "./" + server.data["exe_name"],
            "--config",
            _config_path(server),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Onset using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Onset status is not implemented yet."""


def message(server, msg):
    """Onset has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Onset server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Onset datastore edits."""

    key_path = list(key) if isinstance(key, (list, tuple)) else [key]
    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key_path,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers", "timeout", "iplimit"),
        resolved_str_keys=(
            "servername",
            "servername_short",
            "gamemode",
            "website_url",
            "ipaddress",
            "password",
            "exe_name",
            "dir",
        ),
        backup_module=backup_utils,
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "httpport", "protocol": "tcp"},
    ),
)


get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "queryport", "protocol": "udp"},
        {"key": "httpport", "protocol": "tcp"},
    ),
    stdin_open=True,
)