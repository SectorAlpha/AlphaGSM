"""Kerbal Space Program community-server lifecycle helpers using LunaMultiplayer."""

import os
import stat
import xml.etree.ElementTree as ET

from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

LMP_LATEST_RELEASE_API = "https://api.github.com/repos/LunaMultiplayer/LunaMultiplayer/releases/latest"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Luna Multiplayer in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _resolve_existing_path(server, relative_path):
    """Return the first matching extracted path for a known LMP server file."""

    candidates = (
        os.path.join(server.data["dir"], relative_path),
        os.path.join(server.data["dir"], os.path.basename(relative_path)),
    )
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


def _resolve_config_dir(server):
    """Return the extracted config directory for the current LMP server tree."""

    candidates = (
        os.path.join(server.data["dir"], "LMPServer-linux-x64", "Config"),
        os.path.join(server.data["dir"], "Config"),
    )
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return candidates[0]


def _build_connection_settings_tree(server):
    """Return default connection settings with the managed port."""

    root = ET.Element(
        "ConnectionSettingsDefinition",
        {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        },
    )
    values = (
        ("ListenAddress", "::"),
        ("Port", str(server.data["port"])),
        ("HearbeatMsInterval", "1000"),
        ("ConnectionMsTimeout", "30000"),
        ("Upnp", "true"),
        ("UpnpMsTimeout", "5000"),
        ("MaximumTransmissionUnit", "1408"),
        ("AutoExpandMtu", "false"),
    )
    for key, value in values:
        node = ET.SubElement(root, key)
        node.text = value
    return ET.ElementTree(root)


def _build_general_settings_tree(server):
    """Return default general settings with managed AlphaGSM values."""

    root = ET.Element(
        "GeneralSettingsDefinition",
        {
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
        },
    )
    values = (
        ("ServerName", str(server.data.get("servername") or server.name)),
        ("Description", "Luna Server Description"),
        ("CountryCode", ""),
        ("WebsiteText", "LMP"),
        ("Website", "lunamultiplayer.com"),
        ("Password", ""),
        ("AdminPassword", ""),
        ("ServerMotd", "Hi %Name%!\nWelcome to %ServerName%.\nOnline players: %PlayerCount%"),
        ("PrintMotdInChat", "false"),
        ("MaxPlayers", str(server.data.get("maxplayers") or "20")),
        ("MaxUsernameLength", "15"),
        ("AutoDekessler", "0.5"),
        ("AutoNuke", "0"),
        ("Cheats", "true"),
        ("AllowSackKerbals", "false"),
        ("ConsoleIdentifier", "Server"),
        ("GameDifficulty", "Normal"),
        ("GameMode", "Sandbox"),
        ("ModControl", "true"),
        ("NumberOfAsteroids", "5"),
        ("NumberOfComets", "5"),
        ("TerrainQuality", "High"),
        ("SafetyBubbleDistance", "100"),
        ("MaxVesselParts", "200"),
    )
    for key, value in values:
        node = ET.SubElement(root, key)
        node.text = value
    return ET.ElementTree(root)


def _ensure_settings_tree(path, builder):
    """Return an XML tree from *path*, creating it with *builder* when absent."""

    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        return ET.parse(path)
    tree = builder()
    tree.write(path, encoding="utf-16", xml_declaration=True)
    return tree


def resolve_download(version=None):
    """Resolve the latest LunaMultiplayer server archive."""

    def _matches(asset):
        name = asset.get("name", "")
        return name.endswith(".zip") and "LunaMultiplayer-Server-linux-x64-Release" in name

    from utils.github_releases import resolve_release_asset

    return resolve_release_asset(LMP_LATEST_RELEASE_API, _matches, version=version)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="LMPServer-linux-x64/Server",
):
    """Collect and store configuration values for a KSP LunaMultiplayer server."""

    server.data.setdefault("servername", server.name)
    server.data.setdefault("maxplayers", "20")
    backup_targets = [
        "LMPServer-linux-x64/Config",
        "LMPServer-linux-x64/Universe",
        "LMPServer-linux-x64/logs",
    ]
    server.data.setdefault("backupfiles", backup_targets)
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": backup_targets}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 8800)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the KSP LunaMultiplayer server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input("Direct archive URL for the KSP LunaMultiplayer server: ").strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "LunaMultiplayer-Server-linux-x64-Release.zip"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the KSP LunaMultiplayer server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(server.data["url"]))
    install_archive(server, detect_compression(server.data["download_name"]))


def sync_server_config(server):
    """Sync the managed KSP LunaMultiplayer config files before launch."""

    config_dir = _resolve_config_dir(server)
    connection_path = os.path.join(config_dir, "ConnectionSettings.xml")
    general_path = os.path.join(config_dir, "GeneralSettings.xml")

    connection_tree = _ensure_settings_tree(
        connection_path, lambda: _build_connection_settings_tree(server)
    )
    connection_root = connection_tree.getroot()
    port_node = connection_root.find("Port")
    if port_node is None:
        port_node = ET.SubElement(connection_root, "Port")
    port_node.text = str(server.data["port"])
    connection_tree.write(connection_path, encoding="utf-16", xml_declaration=True)

    general_tree = _ensure_settings_tree(
        general_path, lambda: _build_general_settings_tree(server)
    )
    general_root = general_tree.getroot()
    name_node = general_root.find("ServerName")
    if name_node is None:
        name_node = ET.SubElement(general_root, "ServerName")
    name_node.text = str(server.data.get("servername") or server.name)
    maxplayers_node = general_root.find("MaxPlayers")
    if maxplayers_node is None:
        maxplayers_node = ET.SubElement(general_root, "MaxPlayers")
    maxplayers_node.text = str(server.data.get("maxplayers") or "20")
    general_tree.write(general_path, encoding="utf-16", xml_declaration=True)


def prestart(server):
    """Sync managed config before starting the KSP LunaMultiplayer server."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for KSP LunaMultiplayer."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the address AlphaGSM info should use for KSP LunaMultiplayer."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a KSP LunaMultiplayer server."""

    exe_path = _resolve_existing_path(server, server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    current_mode = os.stat(exe_path).st_mode
    if not current_mode & stat.S_IXUSR:
        os.chmod(exe_path, current_mode | stat.S_IXUSR)
    exe_name = os.path.relpath(exe_path, server.data["dir"])
    return ([exe_name, "--port", str(server.data["port"])], server.data["dir"])


def do_stop(server, j):
    """Stop the KSP LunaMultiplayer server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed KSP LunaMultiplayer status is not implemented yet."""


def message(server, msg):
    """KSP LunaMultiplayer has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a KSP LunaMultiplayer server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported KSP LunaMultiplayer datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("url", "download_name", "exe_name", "dir", "servername", "version"),
    )


config_sync_keys = ("port", "servername", "maxplayers")

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
