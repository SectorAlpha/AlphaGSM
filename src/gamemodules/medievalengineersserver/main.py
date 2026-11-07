"""Medieval Engineers dedicated server lifecycle helpers."""

import os
import shutil
import xml.etree.ElementTree as ET

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 367970
steam_anonymous_login_possible = True
CONTAINER_WORKING_DIR = f"{proton.CONTAINER_SERVER_DIR}/DedicatedServer64"
DEDICATED_CONFIG_NAME = "MedievalEngineers-Dedicated.cfg"
DEFAULT_SCENARIO = "SafeAreaStart"
DEFAULT_MAX_PLAYERS = "8"
config_sync_keys = ("port", "servername", "worldname", "maxplayers")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Medieval Engineers server",
    "The directory to install Medieval Engineers in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Medieval Engineers dedicated server to the latest version.",
    "Restart the Medieval Engineers dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def _container_runtime_env(_server):
    """Return Docker runtime env for the shared wine-proton entrypoint."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 1024x768x24 -nolisten tcp",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }


def _instance_data_dir(server):
    """Return the local dedicated-server data directory."""

    instance_dir = os.path.abspath(os.path.join(server.data["dir"], "instance-data"))
    os.makedirs(instance_dir, exist_ok=True)
    return instance_dir


def _instance_data_path(server):
    """Return the dedicated-server data path expected by the binary."""

    instance_dir = _instance_data_dir(server)
    if IS_LINUX:
        normalized = instance_dir.replace("\\", "/")
        return "Z:" + normalized.replace("/", "\\")
    return instance_dir


def _dedicated_config_path(server):
    """Return the managed dedicated config path."""

    return os.path.join(_instance_data_dir(server), DEDICATED_CONFIG_NAME)


def _build_dedicated_config_tree(server):
    """Return a dedicated config tree aligned with the managed datastore."""

    root = ET.Element(
        "MyConfigDedicated",
        {
            "xmlns:xsd": "http://www.w3.org/2001/XMLSchema",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        },
    )
    session_settings = ET.SubElement(root, "SessionSettings")
    session_values = (
        ("GameMode", "Survival"),
        ("InventorySizeMultiplier", "1"),
        ("OnlineMode", "PUBLIC"),
        ("MaxPlayers", str(server.data.get("maxplayers") or DEFAULT_MAX_PLAYERS)),
        ("MaxFloatingObjects", "64"),
        ("MaxBackupSaves", "5"),
        ("EnableSpectator", "false"),
        ("EnableCopyPaste", "true"),
        ("ShowPlayerNamesOnHud", "true"),
        ("AutoSaveInMinutes", "5"),
        ("ProceduralSeed", "0"),
        ("DestructibleBlocks", "true"),
        ("ViewDistance", "2600"),
        ("Enable3rdPersonView", "true"),
        ("EnableSunRotation", "true"),
        ("PhysicsIterations", "4"),
        ("SunRotationIntervalMinutes", "120"),
        ("DaysPerSeason", "4"),
        ("MaxSolarAltitude", "0.41"),
        ("EnableVoxelDestruction", "true"),
        ("EnableStructuralSimulation", "true"),
        ("MessageOfTheDay", ""),
        ("ServerSideChatLogging", "true"),
        ("EnableLargeDynamicGridDecay", "true"),
        ("ResourceDecayTime", "300"),
        ("AbandonedGridDecayTime", "168"),
        ("MaximumBots", "10"),
        ("EnableHostileAI", "true"),
        ("EnableFastTravel", "true"),
        ("EnableTravelReachability", "true"),
        ("MaxActiveFracturePieces", "50"),
    )
    for key, value in session_values:
        node = ET.SubElement(session_settings, key)
        node.text = value

    ET.SubElement(
        root,
        "Scenario",
        {"Type": "ScenarioDefinition", "Subtype": DEFAULT_SCENARIO},
    )
    ET.SubElement(root, "LoadWorld").text = ""
    ET.SubElement(root, "IP").text = "0.0.0.0"
    ET.SubElement(root, "SteamPort").text = str(int(server.data["port"]) + 1)
    ET.SubElement(root, "ServerPort").text = str(server.data["port"])
    ET.SubElement(root, "AsteroidAmount").text = "4"
    ET.SubElement(root, "Administrators").text = ""
    ET.SubElement(root, "Banned").text = ""
    ET.SubElement(root, "Mods").text = ""
    ET.SubElement(root, "GroupID").text = "0"
    ET.SubElement(root, "ServerName").text = (
        server.data.get("servername") or "AlphaGSM %s" % (server.name,)
    )
    ET.SubElement(root, "WorldName").text = (
        server.data.get("worldname") or server.name
    )
    ET.SubElement(root, "PauseGameWhenEmpty").text = "false"
    ET.SubElement(root, "IgnoreLastSession").text = "false"
    ET.SubElement(root, "RemoteApiEnabled").text = "false"
    ET.SubElement(root, "PublicRemoteApiEnabled").text = "false"
    ET.SubElement(root, "RemoteSecurityKey").text = ""
    ET.SubElement(root, "RemoteApiPort").text = "8080"
    return ET.ElementTree(root)


def sync_server_config(server):
    """Create or update the dedicated config under the managed data path."""

    config_path = _dedicated_config_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    tree = _build_dedicated_config_tree(server)
    if hasattr(ET, "indent"):
        ET.indent(tree, space="  ")
    tree.write(config_path, encoding="utf-8", xml_declaration=True)


def configure(server, ask, port=None, dir=None, *, exe_name="DedicatedServer64/MedievalEngineersDedicated.exe"):
    """Collect and store configuration values for a Medieval Engineers server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "worldname": server.name,
            "maxplayers": DEFAULT_MAX_PLAYERS,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DedicatedServer64", "Content", "instance-data"],
        targets=["DedicatedServer64", "Content", "instance-data"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27016,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Medieval Engineers server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Medieval Engineers server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Medieval Engineers server files and optionally restart the server."

restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Medieval Engineers server."


def prestart(server):
    """Stage Medieval Engineers config before launch."""

    sync_server_config(server)


def _wrap_linux_command(command, wineprefix=None):
    """Wrap Medieval Engineers for a headless Linux process launch."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
        prefer_proton=True,
    )
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = [
        arg
        for arg in wrapped
        if not (
            arg.startswith("DISPLAY=")
            or arg.startswith("WINEDLLOVERRIDES=")
        )
    ]
    wrapped = proton.prepend_env_assignments(
        wrapped,
        SDL_VIDEODRIVER="x11",
        SDL_AUDIODRIVER="dummy",
        WINEDLLOVERRIDES="",
        LIBGL_ALWAYS_SOFTWARE="1",
    )
    return [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        *wrapped,
    ]


def get_start_command(server):
    """Build the command used to launch a Medieval Engineers dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    working_dir = os.path.dirname(exe_path) or server.data["dir"]
    cmd = [
        os.path.basename(server.data["exe_name"]),
        "console",
        "path",
        _instance_data_path(server),
        "port",
        str(server.data["port"]),
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, working_dir


def do_stop(server, j):
    """Stop Medieval Engineers using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Medieval Engineers status is not implemented yet."


def message(server, msg):
    """Medieval Engineers has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Medieval Engineers server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Medieval Engineers datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("exe_name", "dir", "servername", "worldname"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        prefer_proton=True,
        extra_env=_container_runtime_env,
        extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    prefer_proton=True,
    extra_env=_container_runtime_env,
    working_dir=CONTAINER_WORKING_DIR,
)
