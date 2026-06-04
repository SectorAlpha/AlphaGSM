"""CryoFall dedicated server lifecycle helpers."""

import os
import xml.etree.ElementTree as ET

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1061710
steam_anonymous_login_possible = True
TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "settings_server_template.xml"
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the CryoFall server",
    "The directory to install CryoFall in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the CryoFall dedicated server to the latest version.",
    "Restart the CryoFall dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "servername", "maxplayers")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="Binaries/Server/CryoFall_Server.dll",
):
    """Collect and store configuration values for a CryoFall server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": "100",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Data"],
        targets=["Data"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=6000,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the CryoFall server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    server.data.setdefault("dotnetpath", "dotnet")
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the CryoFall server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the CryoFall server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the CryoFall server."


def sync_server_config(server):
    """Create or update Data/SettingsServer.xml with managed settings."""

    if not server.data.get("dir"):
        return

    data_dir = os.path.join(server.data["dir"], "Data")
    config_path = os.path.join(data_dir, "SettingsServer.xml")
    os.makedirs(data_dir, exist_ok=True)
    if not os.path.isfile(config_path):
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as src:
            with open(config_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())

    tree = ET.parse(config_path)
    root = tree.getroot()

    network = root.find("network")
    if network is None:
        network = ET.SubElement(root, "network")
    port_node = network.find("port")
    if port_node is None:
        port_node = ET.SubElement(network, "port")
    port_node.text = str(server.data["port"])

    server_node = root.find("server")
    if server_node is None:
        server_node = ET.SubElement(root, "server")
    name_node = server_node.find("name")
    if name_node is None:
        name_node = ET.SubElement(server_node, "name")
    name_node.text = server.data.get("servername") or "AlphaGSM %s" % (server.name,)
    players_node = server_node.find("players_max_count")
    if players_node is None:
        players_node = ET.SubElement(server_node, "players_max_count")
    players_node.text = str(server.data.get("maxplayers") or "100")

    tree.write(config_path, encoding="utf-8", xml_declaration=True)


def prestart(server):
    """Stage CryoFall settings before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for CryoFall."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for CryoFall."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a CryoFall server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return [
        server.data.get("dotnetpath", "dotnet"),
        server.data["exe_name"],
        "loadOrNew",
    ], server.data["dir"]


def do_stop(server, j):
    """Stop CryoFall using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed CryoFall status is not implemented yet."""


def message(server, msg):
    """CryoFall has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a CryoFall server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported CryoFall datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("exe_name", "dir", "servername", "dotnetpath"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra={'host_dependencies': ({'id': 'dotnet', 'display_name': '.NET', 'command_key': 'dotnetpath', 'command': 'dotnet'},)},
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
