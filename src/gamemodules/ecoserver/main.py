"""Eco dedicated server lifecycle helpers."""

import json
import os

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 739590
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Eco in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Eco dedicated server to the latest version.",
    "Restart the Eco dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def _network_config_path(server):
    """Return the effective Eco network config path."""

    return os.path.join(server.data["dir"], "Configs", "Network.eco")


def _network_config_template_path(server):
    """Return the shipped Eco network config template path."""

    return os.path.join(server.data["dir"], "Configs", "Network.eco.template")


def _derived_port(server, offset):
    """Return a port derived from Eco's base game port."""

    return int(server.data.get("port", 3000)) + int(offset)


def _ensure_local_steam_bootstrap(install_dir):
    """Seed Steam bootstrap files inside the Eco install tree."""

    steam_appid_path = os.path.join(install_dir, "steam_appid.txt")
    with open(steam_appid_path, "w", encoding="utf-8") as handle:
        handle.write(f"{steam_app_id}\n")

    steamclient_src = os.path.join(install_dir, "linux64", "steamclient.so")
    if not os.path.isfile(steamclient_src):
        return

    sdk_dir = os.path.join(install_dir, ".steam", "sdk64")
    os.makedirs(sdk_dir, exist_ok=True)
    steamclient_dst = os.path.join(sdk_dir, "steamclient.so")
    steamclient_relpath = os.path.relpath(steamclient_src, sdk_dir)
    if os.path.lexists(steamclient_dst):
        if os.path.islink(steamclient_dst) and os.readlink(steamclient_dst) == steamclient_relpath:
            return
        os.remove(steamclient_dst)
    os.symlink(steamclient_relpath, steamclient_dst)


def _bundle_extract_dir(install_dir):
    """Return Eco's writable .NET bundle extraction directory."""

    return os.path.join(install_dir, ".net-bundle-cache")


def _libgdiplus_host_dependency():
    """Describe Eco's shared libgdiplus runtime dependency."""

    return {
        "id": "libgdiplus",
        "display_name": "libgdiplus",
        "kind": "shared-library",
        "library_names": {
            "linux": "libgdiplus.so",
        },
        "install_hints": {
            "linux": "Install the host package 'libgdiplus' before launching Eco locally, or switch this server to the Docker runtime instead.",
            "macos": "Install libgdiplus (for example via Homebrew's mono stack) before launching Eco locally on macOS, or switch this server to the Docker runtime instead.",
            "windows": "Install the required System.Drawing/libgdiplus runtime dependency before launching Eco locally on Windows, or switch this server to the Docker runtime instead.",
        },
    }


def _network_config_defaults():
    """Return base defaults for Eco's ``Network.eco`` payload."""

    return {
        "PublicServer": False,
        "Playtime": "",
        "DiscordAddress": "",
        "Password": "",
        "Name": "",
        "DetailedDescription": "",
        "ServerCategory": "None",
        "IPAddress": "Any",
        "RemoteAddress": "",
        "WebServerUrl": "",
        "RconIPAddress": "Any",
        "RconPassword": "",
        "Rate": 20,
        "DefaultSlots": -1,
        "ReservedSlots": 5,
        "MaxUsersLoadingAtSameTime": 20,
        "UPnPEnabled": True,
        "RelayServerAddress": "",
    }


def sync_server_config(server):
    """Write Eco's ``Network.eco`` so derived side ports follow the base port."""

    config_dir = os.path.dirname(_network_config_path(server))
    os.makedirs(config_dir, exist_ok=True)

    config = _network_config_defaults()
    config_path = _network_config_path(server)
    template_path = _network_config_template_path(server)
    source_path = config_path if os.path.isfile(config_path) else template_path
    if os.path.isfile(source_path):
        try:
            with open(source_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                config.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass

    base_port = int(server.data.get("port", 3000))
    config["GameServerPort"] = base_port
    config["WebServerPort"] = _derived_port(server, 1)
    config["RconServerPort"] = _derived_port(server, 2)
    config["SteamServerPort"] = _derived_port(server, 3)

    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")


def configure(server, ask, port=None, dir=None, *, exe_name="EcoServer"):
    """Collect and store configuration values for an Eco server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "world": server.name,
            "storage": "Storage",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Storage", "Configs"],
        targets=["Storage", "Configs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=3000,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Eco server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_install_hook = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
_install_hook.__doc__ = "Download the Eco server files via SteamCMD."


def install(server):
    """Download Eco via SteamCMD and sync the managed network config."""

    _install_hook(server)
    _ensure_local_steam_bootstrap(os.path.normpath(server.data["dir"]))
    os.makedirs(_bundle_extract_dir(os.path.normpath(server.data["dir"])), exist_ok=True)
    sync_server_config(server)


_update_hook = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def update(server, *args, **kwargs):
    """Update Eco and refresh the managed network config."""

    _update_hook(server, *args, **kwargs)
    _ensure_local_steam_bootstrap(os.path.normpath(server.data["dir"]))
    os.makedirs(_bundle_extract_dir(os.path.normpath(server.data["dir"])), exist_ok=True)
    sync_server_config(server)


restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch an Eco dedicated server."""

    install_dir = os.path.normpath(server.data["dir"])
    _ensure_local_steam_bootstrap(install_dir)
    os.makedirs(_bundle_extract_dir(install_dir), exist_ok=True)
    exe_path = os.path.join(install_dir, server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "env",
            "HOME=.",
            "LD_LIBRARY_PATH=.:./linux64",
            "DOTNET_BUNDLE_EXTRACT_BASE_DIR=.net-bundle-cache",
            "./" + server.data["exe_name"],
            "-nogui",
            "-offline",
            "-port",
            str(server.data["port"]),
            "-world",
            server.data["world"],
            "-storedirectory",
            server.data["storage"],
        ],
        server.data["dir"],
    )


def prestart(server):
    """Refresh Eco's managed network config before each launch."""

    install_dir = os.path.normpath(server.data["dir"])
    _ensure_local_steam_bootstrap(install_dir)
    os.makedirs(_bundle_extract_dir(install_dir), exist_ok=True)
    sync_server_config(server)


def do_stop(server, j):
    """Stop Eco using the standard save-and-shutdown command."""

    runtime_module.send_to_server(server, "\nsave\nshutdown\n")


def status(server, verbose):
    """Detailed Eco status is not implemented yet."""


def message(server, msg):
    """Eco has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Eco server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Eco datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("world", "storage", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")


def get_runtime_requirements(server):
    """Publish Eco's base gameplay port plus its web/RCON/Steam side ports."""

    server.data["webport"] = str(_derived_port(server, 1))
    server.data["rconport"] = str(_derived_port(server, 2))
    server.data["steamport"] = str(_derived_port(server, 3))
    return gamemodule_common.make_runtime_requirements_builder(
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
            {"key": "webport", "protocol": "tcp"},
            {"key": "rconport", "protocol": "tcp"},
            {"key": "steamport", "protocol": "udp"},
        ),
        extra={
            "host_dependencies": [
                _libgdiplus_host_dependency(),
            ],
        },
    )(server)


def get_container_spec(server):
    """Expose Eco's published gameplay and side-port contract for Docker."""

    return gamemodule_common.make_container_spec_builder(
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
            {"key": "webport", "protocol": "tcp"},
            {"key": "rconport", "protocol": "tcp"},
            {"key": "steamport", "protocol": "udp"},
        ),
        stdin_open=True,
        tty=False,
        extra={"stop_mode": "exec-console"},
    )(server)
