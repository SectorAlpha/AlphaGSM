"""FOUNDRY dedicated server lifecycle helpers."""

import os
import socket

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2915550
# Official FoundryDedicatedServerLauncher.bat writes the game client id here.
# The dedicated-server tool id is steam_app_id; Steam query uses the client id.
GAME_APP_ID = 983870
steam_anonymous_login_possible = True
# App 2915550 publishes a Windows depot only. Linux runs that build under Wine.
DEFAULT_EXE_NAME = "FoundryDedicatedServer.exe"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the FOUNDRY server",
    "The directory to install FOUNDRY in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the FOUNDRY dedicated server to the latest version.",
    "Restart the FOUNDRY dedicated server.",
)
command_functions = {}
max_stop_wait = 1
# Steam answers A2S on server_query_port only when server_is_public is true.
# https://dedicated.foundry-game.com/
DEFAULT_QUERY_PORT = 27015
config_sync_keys = ("port", "queryport", "servername", "worldname")
_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "queryport", "protocol": "udp", "default": DEFAULT_QUERY_PORT},
)


def _port_is_bindable(port):
    """Return whether TCP and UDP can both bind this wildcard port."""

    for socktype in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        probe = socket.socket(socket.AF_INET, socktype)
        try:
            probe.bind(("0.0.0.0", int(port)))
        except OSError:
            return False
        finally:
            probe.close()
    return True


def _select_query_port(game_port):
    """Use the documented query port unless it is already taken or is the game port."""

    blocked = set()
    if game_port not in (None, ""):
        blocked.add(int(game_port))
    if DEFAULT_QUERY_PORT not in blocked and _port_is_bindable(DEFAULT_QUERY_PORT):
        return DEFAULT_QUERY_PORT
    for offset in range(1, 100):
        candidate = DEFAULT_QUERY_PORT + offset
        if candidate > 65535 or candidate in blocked:
            continue
        if _port_is_bindable(candidate):
            return candidate
    return DEFAULT_QUERY_PORT


def configure(server, ask, port=None, dir=None, *, exe_name=DEFAULT_EXE_NAME):
    """Collect and store configuration values for a FOUNDRY server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "worldname": server.name,
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["saves", "configs"],
        targets=["saves", "configs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=37200,
        prompt="Please specify the game port to use for this server:",
    )
    if "queryport" not in server.data:
        server.data["queryport"] = _select_query_port(server.data.get("port"))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the FOUNDRY server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    if IS_LINUX and "wineprefix" not in server.data:
        server.data["wineprefix"] = os.path.join(server.data["dir"], "wineprefix")
    return gamemodule_common.finalize_configure(server)


def _install_file(server, name):
    """Return a path beside the dedicated-server executable."""

    exe_name = server.data.get("exe_name", DEFAULT_EXE_NAME)
    return os.path.join(server.data["dir"], os.path.dirname(exe_name), name)


def _app_cfg_path(server):
    """Return app.cfg beside the dedicated-server executable."""

    return _install_file(server, "app.cfg")


def _cfg_assignment_key(line):
    """Return the key of a non-comment app.cfg assignment, if any."""

    stripped = line.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith(";") or "=" not in stripped:
        return None
    key, _value = stripped.split("=", 1)
    key = key.strip()
    if not key or any(char.isspace() for char in key):
        return None
    return key


def _cfg_value(value):
    """Return a single-line app.cfg value."""

    return str(value).replace("\r", " ").replace("\n", " ").strip()


def sync_server_config(server):
    """Write app.cfg so the existing A2S hook can reach a public query port."""

    install_dir = server.data.get("dir")
    if not install_dir or "port" not in server.data:
        return
    if "queryport" not in server.data:
        server.data["queryport"] = DEFAULT_QUERY_PORT
        save = getattr(server.data, "save", None)
        if callable(save):
            save()
    updates = {
        "server_name": _cfg_value(server.data.get("servername") or ("AlphaGSM %s" % (server.name,))),
        "server_world_name": _cfg_value(server.data.get("worldname") or server.name),
        "server_port": str(int(server.data["port"])),
        "server_query_port": str(int(server.data.get("queryport", DEFAULT_QUERY_PORT))),
        "server_is_public": "true",
        # An empty proof server must keep the Steam query socket open.
        "pause_server_when_empty": "false",
    }
    path = _app_cfg_path(server)
    lines = []
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    seen = set()
    rendered = []
    for line in lines:
        key = _cfg_assignment_key(line)
        if key in updates:
            rendered.append("%s=%s" % (key, updates[key]))
            seen.add(key)
        else:
            rendered.append(line)
    for key in (
        "server_name",
        "server_world_name",
        "server_port",
        "server_query_port",
        "server_is_public",
        "pause_server_when_empty",
    ):
        if key not in seen:
            rendered.append("%s=%s" % (key, updates[key]))
    text = "\n".join(rendered)
    if text and not text.endswith("\n"):
        text += "\n"
    os.makedirs(os.path.dirname(path) or install_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    appid_path = _install_file(server, "steam_appid.txt")
    with open(appid_path, "w", encoding="utf-8") as handle:
        handle.write("%s\n" % (GAME_APP_ID,))


def prestart(server):
    """Refresh app.cfg before launch so Steam A2S is enabled."""

    sync_server_config(server)


def install(server):
    """Download FOUNDRY via SteamCMD or require a staged native server tree."""

    os.makedirs(server.data["dir"], exist_ok=True)
    download_kwargs = {"force_windows": True} if IS_LINUX else {}
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        **download_kwargs,
    )
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "foundryserver",
            "stage a native FOUNDRY dedicated server tree containing "
            "FoundryDedicatedServer in <install_dir> before setup/start",
        )
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)


restart = gamemodule_common.make_restart_hook()


def get_query_address(server):
    """FOUNDRY serves A2S on the dedicated query port when the server is public."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a FOUNDRY dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        gamemodule_common.raise_byo_requirement(
            "foundryserver",
            "stage a native FOUNDRY dedicated server tree containing "
            "FoundryDedicatedServer in <install_dir> before setup/start",
        )
    command = [
        "./" + server.data["exe_name"],
        "--world",
        server.data["worldname"],
        "--name",
        server.data["servername"],
        "--port",
        str(server.data["port"]),
    ]
    if IS_LINUX and str(server.data["exe_name"]).lower().endswith(".exe"):
        wineprefix = server.data.get("wineprefix") or os.path.join(server.data["dir"], "wineprefix")
        command = proton.wrap_xvfb_command(
            command,
            wineprefix=wineprefix,
            prefer_proton=False,
        )
        command = proton.prepend_env_assignments(
            command,
            SteamAppId=str(GAME_APP_ID),
            SteamGameId=str(GAME_APP_ID),
            WINEDEBUG="-all",
        )
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop FOUNDRY using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed FOUNDRY status is not implemented yet."""


def message(server, msg):
    """FOUNDRY has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a FOUNDRY server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported FOUNDRY datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport"):
        return int(value[0])
    if key[0] in ("worldname", "servername", "exe_name", "dir", "wineprefix"):
        return str(value[0])
    raise ServerError("Unsupported key")

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
