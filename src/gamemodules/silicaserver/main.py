"""Silica dedicated server lifecycle helpers."""

import os
import xml.etree.ElementTree as ET

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2738040
steam_anonymous_login_possible = True
_PORT_DEFINITIONS = (
    {"key": "queryport", "protocol": "udp"},
    {"key": "port", "protocol": "udp"},
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Silica server",
    "The directory to install Silica in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Silica dedicated server to the latest version.",
    "Restart the Silica dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "maxplayers", "servername")
setting_schema = {
    "servername": SettingSpec(
        canonical_key="servername", aliases=("hostname",),
        description="Name advertised by the Silica server.",
        value_type="string", apply_to=("datastore", "native_config"),
        native_config_key="ServerName",
    ),
}


def _runtime_home(server):
    return os.path.join(os.path.abspath(server.data["dir"]), ".alphagsm-home")


def sync_server_config(server):
    """Preserve native XML settings while applying managed network and player values."""

    if "dir" not in server.data or "port" not in server.data:
        return
    path = os.path.join(_runtime_home(server), "Silica", "ServerSettings.xml")
    source = path if os.path.isfile(path) else os.path.expanduser("~/Silica/ServerSettings.xml")
    if os.path.isfile(source):
        try:
            tree = ET.parse(source, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
        except ET.ParseError as exc:
            raise ServerError(f"Invalid Silica server settings: {source}: {exc}") from exc
        root = tree.getroot()
        if root.tag != "NetworkServerSettings":
            raise ServerError("Silica settings must use a NetworkServerSettings root")
    else:
        root = ET.Element("NetworkServerSettings", {
            "CurrentGameMode": "MP_Strategy", "Singleplayer": "false",
            "PasswordProtected": "false", "ServerPassword": "",
        })
        ET.SubElement(root, "GameModeSettings", {
            "GameMode": "MP_Strategy", "CurrentMap": "MonumentValley",
            "MapList": "MonumentValley",
        })
        tree = ET.ElementTree(root)
    root.set("GamePort", str(server.data["port"]))
    root.set("QueryPort", str(server.data.get("queryport", 26901)))
    root.set("ServerName", str(server.data.get("servername", f"AlphaGSM {server.name}")))
    current_mode = root.get("CurrentGameMode", "MP_Strategy")
    game_settings = next(
        (entry for entry in root.findall("GameModeSettings") if entry.get("GameMode") == current_mode),
        None,
    )
    if game_settings is None:
        raise ServerError(f"Silica settings have no GameModeSettings for {current_mode}")
    game_settings.set("MaxPlayers", str(server.data.get("maxplayers", 64)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def configure(server, ask, port=None, dir=None, *, exe_name="Silica.x86_64"):
    """Collect and store configuration values for a Silica server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "26901",
            "maxplayers": "64",
            "servername": f"AlphaGSM {server.name}",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Silica_Data", "Config", "Saved", ".alphagsm-home/Silica"],
        targets=["Config", "Saved", ".alphagsm-home/Silica"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=26900,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Silica server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Silica server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Silica server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Silica server."


def _native_start_command(server):
    """Build native Unity arguments; game settings come from ServerSettings.xml."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-batchmode",
            "-nographics",
        ],
        server.data["dir"],
    )


def get_start_command(server):
    """Launch with an isolated HOME containing this instance's native XML."""

    command, cwd = _native_start_command(server)
    return ["env", f"HOME={_runtime_home(server)}", *command], cwd


def prestart(server):
    """Sync native settings and expose Steam's SDK inside the process HOME."""

    sync_server_config(server)
    source = os.path.join(steamcmd.STEAMCMD_DIR, "linux64", "steamclient.so")
    if os.path.isfile(source):
        target = os.path.join(_runtime_home(server), ".steam", "sdk64", "steamclient.so")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if not os.path.lexists(target):
            os.symlink(os.path.abspath(source), target)


def do_stop(server, j):
    """Stop Silica by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Silica status is not implemented yet."""


def message(server, msg):
    """Silica has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Silica server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Silica datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_str_keys=("servername",),
        raw_int_keys=("port", "queryport", "maxplayers"),
        raw_str_keys=("exe_name", "dir"),
    )

def get_query_address(server):
    """Query Silica's Steam server listener using the native XML query port."""

    return runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s"


def get_info_address(server):
    """Use the native Steam query endpoint for server information."""

    return get_query_address(server)


def get_runtime_requirements(server):
    """Persist the isolated HOME alongside the shared Steam SDK mounts."""

    requirements = runtime_module.build_runtime_requirements(
        server, family="steamcmd-linux", port_definitions=_PORT_DEFINITIONS,
        env={"HOME": "/root"},
    )
    if "dir" in server.data:
        requirements.setdefault("mounts", []).append({
            "source": _runtime_home(server), "target": "/root", "mode": "rw",
        })
    return requirements


def get_container_spec(server):
    """Use the same XML as process runtime with Docker-visible HOME and SDK paths."""

    return runtime_module.build_container_spec(
        server, family="steamcmd-linux", get_start_command=_native_start_command,
        port_definitions=_PORT_DEFINITIONS, env={"HOME": "/root"},
        mounts=get_runtime_requirements(server).get("mounts", []), stdin_open=True,
    )
