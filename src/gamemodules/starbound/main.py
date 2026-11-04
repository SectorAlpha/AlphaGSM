"""Starbound dedicated server lifecycle helpers."""

import json
import os

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 211820
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Starbound in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Starbound dedicated server to the latest version.",
    "Restart the Starbound dedicated server.",
)
command_functions = {}
max_stop_wait = 1
# Starbound's UDP query socket stays closed unless runQueryServer is true.
# The stock query port is the game port. https://starbounder.org/Guide:Setting_Up_Multiplayer
DEFAULT_PORT = 21025
config_sync_keys = ("port",)
_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "tcp"},
    {"key": "port", "protocol": "udp", "default": DEFAULT_PORT},
)


def configure(server, ask, port=None, dir=None, *, exe_name="linux64/starbound_server"):
    """Collect and store configuration values for a Starbound server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["giraffe_storage", "linux64/sbboot.config"],
        targets=["giraffe_storage", "linux64/sbboot.config"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=DEFAULT_PORT,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Starbound server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _server_config_path(server):
    """Return the dedicated server's JSON config under storage/."""

    return os.path.join(server.data["dir"], "storage", "starbound_server.config")


def _default_server_config(server, port):
    """Return a complete config the dedicated server will keep."""

    return {
        "allowAdminCommands": True,
        "allowAdminCommandsFromAnyone": False,
        "allowAnonymousConnections": True,
        "allowAssetsMismatch": True,
        "anonymousConnectionsAreAdmin": False,
        "bannedIPs": [],
        "bannedUuids": [],
        "checkAssetsDigest": False,
        "clearPlayerFiles": False,
        "clearUniverseFiles": False,
        "clientIPJoinable": True,
        "clientP2PJoinable": False,
        "configurationVersion": {"basic": 2, "server": 4},
        "crafting": {"filterHaveMaterials": False},
        "gameServerBind": "::",
        "gameServerPort": port,
        "interactiveHighlight": True,
        "inventory": {"pickupToActionBar": True},
        "maxPlayers": 8,
        "maxTeamSize": 4,
        "monochromeLighting": False,
        "playerBackupFileCount": 3,
        "queryServerBind": "::",
        "queryServerPort": port,
        "rconServerBind": "::",
        "rconServerPassword": "",
        "rconServerPort": 21026 if port != 21026 else 21027,
        "rconServerTimeout": 1000,
        "runQueryServer": True,
        "runRconServer": False,
        "safeScripts": True,
        "scriptInstructionLimit": 10000000,
        "scriptInstructionMeasureInterval": 10000,
        "scriptProfilingEnabled": False,
        "scriptRecursionLimit": 100,
        "serverFidelity": "automatic",
        "serverName": server.data.get("servername") or ("AlphaGSM %s" % (server.name,)),
        "serverOverrideAssetsDigest": None,
        "serverUsers": {},
        "tutorialMessages": True,
    }


def sync_server_config(server):
    """Enable Starbound's query server on the port the existing A2S hook uses."""

    install_dir = server.data.get("dir")
    if not install_dir or "port" not in server.data:
        return
    port = int(server.data["port"])
    path = _server_config_path(server)
    payload = None
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
        if raw.strip():
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ServerError("Invalid Starbound server config: %s: %s" % (path, exc)) from exc
            if not isinstance(payload, dict):
                raise ServerError("Starbound server config must be a JSON object: %s" % (path,))
    if payload is None:
        payload = _default_server_config(server, port)
    payload["gameServerPort"] = port
    payload["queryServerPort"] = port
    payload["runQueryServer"] = True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def prestart(server):
    """Refresh starbound_server.config before launch so A2S is enabled."""

    sync_server_config(server)


_LINUX_SERVER_BINARIES = ("linux64/starbound_server", "linux/starbound_server")


def _byo_server_message():
    """Explain the native Linux tree an empty anonymous install cannot replace."""

    return (
        "stage a native Starbound server tree containing linux64/starbound_server "
        "or linux/starbound_server and assets/packed.pak "
        "in <install_dir> before setup/start"
    )


def _ensure_linux_executable(server):
    """Keep the configured Linux binary, or the owned tree's Linux server."""

    install_dir = server.data["dir"]
    ordered = []
    current = server.data.get("exe_name")
    if current:
        ordered.append(current)
    for relative in _LINUX_SERVER_BINARIES:
        if relative not in ordered:
            ordered.append(relative)
    for relative in ordered:
        path = os.path.join(install_dir, relative)
        if os.path.isfile(path):
            if server.data.get("exe_name") != relative:
                server.data["exe_name"] = relative
                save = getattr(server.data, "save", None)
                if callable(save):
                    save()
            os.chmod(path, os.stat(path).st_mode | 0o755)
            return path
    return None


def install(server):
    """Download Starbound via SteamCMD or require a staged native server tree."""

    os.makedirs(server.data["dir"], exist_ok=True)
    # A saved profile must stay authenticated. Anonymous app 211820 mounts no
    # depots and would replace an owned tree with an empty install.
    auth_profile = server.data.get("steam_auth_profile")
    download_kwargs = {}
    if auth_profile:
        download_kwargs["auth_profile"] = auth_profile
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        **download_kwargs,
    )
    if _ensure_linux_executable(server) is None:
        gamemodule_common.raise_byo_requirement("starbound", _byo_server_message())
    sync_server_config(server)


def _download_kwargs(server):
    """Keep an owned update on the saved profile.

    Anonymous app 211820 mounts no depots, so an update without the profile
    would replace the entitled Linux tree with an empty install.
    """

    profile = server.data.get("steam_auth_profile")
    if profile:
        return {"auth_profile": profile}
    return {}


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs=_download_kwargs,
)
update.__doc__ = "Update the Starbound server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Starbound server."


def get_query_address(server):
    """Starbound serves A2S on the game port when runQueryServer is enabled."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Starbound dedicated server.

    sbinit.config lives beside the binary and resolves assets with paths such
    as ../assets, so the working directory has to be that Linux server folder.
    """

    if _ensure_linux_executable(server) is None:
        gamemodule_common.raise_byo_requirement("starbound", _byo_server_message())
    relative = server.data["exe_name"]
    folder = os.path.dirname(relative)
    cwd = os.path.join(server.data["dir"], folder) if folder else server.data["dir"]
    return ["./" + os.path.basename(relative)], cwd


def do_stop(server, j):
    """Send a shutdown command to Starbound."""

    runtime_module.send_to_server(server, "\nshutdown\n")


def status(server, verbose):
    """Detailed Starbound status is not implemented yet."""


def message(server, msg):
    """Starbound has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Starbound server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Starbound datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=_PORT_DEFINITIONS,
)

get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=_PORT_DEFINITIONS,
    stdin_open=True,
)


def get_asset_requirements(server):
    """Describe this game's owned files, acquisition routes and staging limits."""
    from utils.byo_files import load_requirements
    return load_requirements(server, __file__, 'byo_assets.json')
