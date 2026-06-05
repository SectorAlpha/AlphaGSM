"""Heat dedicated server lifecycle helpers."""

import os
import re
import shutil
import subprocess
import time

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 996600
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Heat server",
    "The directory to install Heat in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Heat dedicated server to the latest version.",
    "Restart the Heat dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "maxplayers", "startmap")
_BOOTSTRAP_CONFIG_TIMEOUT_SECONDS = 120
_DEFAULT_SERVER_SETTINGS_TEMPLATE = """version = '5'

# -- Server --
isPrivate = 'False'
serverName = '{servername}'
greeting = 'Welcome to {servername}!'
maxPlayers = '{maxplayers}'
bindIP = '0.0.0.0'
portNumber = '{port}'
password = ''
restartInterval = '28800'
restartHour = '-1'
restartMessage = 'The server will restart in %timeLeft%.'
Restart Warning Times {{
- '3600'
- '1800'
- '600'
- '300'
- '30'
}}
enableCommands = 'True'
connectionTimeout = '600'
steamAuthTimeout = '600'
steamAuthPort = '{queryport}'
asyncPort = '{asyncport}'
timeBetweenPlayerJoin = '10'
targetFrameRate = '60'

# -- Ping Limit --
enablePingLimit = 'False'
pingPort = '{pingport}'
pingLimit = '250'
pingGraphLength = '360'

# -- World --
saveLocation = 'Saves/'
autoSaveInterval = '3600'
worldSlot = '1'
allowSaving = 'True'
levelName = '{startmap}'

# -- Backups --
backupsEnabled = 'True'
"""


def configure(server, ask, port=None, dir=None, *, exe_name="Server.exe"):
    """Collect and store configuration values for a Heat server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27016",
            "maxplayers": "32",
            "startmap": "America",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved", "ServerConfig.cfg"],
        targets=["Saved", "ServerConfig.cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Heat server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Heat server."


def get_query_address(server):
    """Heat uses Steam A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def _server_settings_path(server):
    """Return the Heat server settings path."""

    return os.path.join(server.data["dir"], "Configuration", "ServerSettings.cfg")


def _build_default_server_settings(server):
    """Return a baseline Heat server config when bootstrap cannot generate one."""

    port = int(server.data.get("port", 27015))
    queryport = int(server.data.get("queryport", 27016))
    maxplayers = int(server.data.get("maxplayers", 32))
    startmap = str(server.data.get("startmap", "America"))
    servername = str(server.data.get("servername", f"AlphaGSM {server.name}"))
    return _DEFAULT_SERVER_SETTINGS_TEMPLATE.format(
        servername=servername.replace("'", "\\'"),
        maxplayers=maxplayers,
        port=port,
        queryport=queryport,
        asyncport=port + 4,
        pingport=port,
        startmap=startmap.replace("'", "\\'"),
    )


def _write_default_server_settings(server):
    """Write a baseline Heat server config when bootstrap cannot generate one."""

    config_path = _server_settings_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as fh:
        fh.write(_build_default_server_settings(server))
    return config_path


def _replace_cfg_value(config_text, key, value):
    """Replace one scalar setting in the Heat cfg text."""

    updated_text, replacements = re.subn(
        rf"(^\s*{re.escape(key)}\s*=\s*')(.*?)('.*$)",
        rf"\g<1>{value}\g<3>",
        config_text,
        count=1,
        flags=re.MULTILINE,
    )
    if replacements == 0:
        raise ServerError(f"Heat server config is missing {key}")
    return updated_text


def sync_server_config(server):
    """Keep Heat's native server settings aligned with AlphaGSM values."""

    if not server.data.get("dir"):
        return
    config_path = _server_settings_path(server)
    if not os.path.isfile(config_path):
        return
    with open(config_path, encoding="utf-8") as fh:
        config_text = fh.read()
    updated_text = config_text
    replacements = (
        ("portNumber", int(server.data.get("port", 27015))),
        ("steamAuthPort", int(server.data.get("queryport", 27016))),
        ("maxPlayers", int(server.data.get("maxplayers", 32))),
        ("levelName", str(server.data.get("startmap", "America"))),
    )
    for key, value in replacements:
        updated_text = _replace_cfg_value(updated_text, key, value)
    if updated_text != config_text:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(updated_text)


def _bootstrap_server_settings_if_missing(server):
    """Run the upstream first-launch config generation once when needed."""

    config_path = _server_settings_path(server)
    if os.path.isfile(config_path):
        return

    command, cwd = get_start_command(server)
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        command,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + _BOOTSTRAP_CONFIG_TIMEOUT_SECONDS
    try:
        while time.monotonic() < deadline:
            if os.path.isfile(config_path):
                return
            if process.poll() is not None:
                break
            time.sleep(1)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)

    if os.path.isfile(config_path):
        return

    _write_default_server_settings(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Heat server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Heat server files and optionally restart the server."


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows server command for headless Linux hosts."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
        prefer_proton=True,
    )
    wrapped = proton.prepend_env_assignments(
        wrapped,
        TERM="dumb",
    )
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = proton.prepend_env_assignments(
        wrapped,
        SDL_VIDEODRIVER="x11",
        SDL_AUDIODRIVER="dummy",
    )
    wrapped = [
        arg
        for arg in wrapped
        if not (
            arg.startswith("DISPLAY=")
            or arg.startswith("WINEDLLOVERRIDES=")
        )
    ]
    return [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        *wrapped,
    ]


def get_start_command(server):
    """Build the command used to launch a Heat dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"]]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


def prestart(server):
    """Refresh Heat's native server config before each launch."""

    _bootstrap_server_settings_if_missing(server)
    sync_server_config(server)


def do_stop(server, j):
    """Stop Heat using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Heat status is not implemented yet."""


def message(server, msg):
    """Heat has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Heat server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Heat datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("startmap", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
