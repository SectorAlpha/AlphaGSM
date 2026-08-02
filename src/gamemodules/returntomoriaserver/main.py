"""Return to Moria dedicated server lifecycle helpers."""

import configparser
import os
import signal
import subprocess

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3349480
steam_anonymous_login_possible = True
DEFAULT_PORT = 7777
DEFAULT_WORLD_NAME = "Dedicated Server World"
PREFER_PROTON = True


def _container_runtime_env(_server):
    """Return the Docker display requirements for the Windows server."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 1024x768x24 -nolisten tcp",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }


commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Return to Moria server",
    "The directory to install Return to Moria in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Return to Moria dedicated server to the latest version.",
    "Restart the Return to Moria dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "advertiseaddress", "worldname")


def configure(server, ask, port=None, dir=None, *, exe_name="MoriaServer.exe"):
    """Collect and store configuration values for a Return to Moria server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "advertiseaddress": "local",
            "worldname": DEFAULT_WORLD_NAME,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=[
            "Moria/Saved/SaveGamesDedicated",
            "MoriaServerConfig.ini",
            "MoriaServerPermissions.txt",
            "MoriaServerRules.txt",
        ],
        targets=[
            "Moria/Saved/SaveGamesDedicated",
            "MoriaServerConfig.ini",
            "MoriaServerPermissions.txt",
            "MoriaServerRules.txt",
        ],
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
        prompt="Where would you like to install the Return to Moria server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _config_path(server):
    return os.path.join(server.data["dir"], "MoriaServerConfig.ini")


def sync_server_config(server):
    """Keep Return to Moria's managed config aligned with AlphaGSM settings."""

    if not server.data.get("dir"):
        return
    parser = configparser.RawConfigParser(interpolation=None)
    parser.optionxform = str
    config_path = _config_path(server)
    if os.path.isfile(config_path):
        parser.read(config_path, encoding="utf-8")

    defaults = {
        "Main": {
            "OptionalPassword": "",
        },
        "World": {
            "Name": '"{}"'.format(server.data.get("worldname", DEFAULT_WORLD_NAME)),
            "OptionalWorldFilename": "",
        },
        "World.Create": {
            "Type": "campaign",
            "Seed": "random",
            "Difficulty.Preset": "normal",
            'OptionalDLC.Array': '"DurinsFolk"',
            'UpgradeOptionalDLC.Array': '""',
        },
        "Host": {
            "ListenAddress": "",
            "ListenPort": str(server.data.get("port", DEFAULT_PORT)),
            "AdvertiseAddress": str(server.data.get("advertiseaddress", "local")),
            "AdvertisePort": str(server.data.get("port", DEFAULT_PORT)),
            "InitialConnectionRetryTime": "120",
            "AfterDisconnectionRetryTime": "600",
        },
        "Console": {
            # The server uses the enabled console to complete world startup.
            "Enabled": "true",
        },
        "Performance": {
            "ServerFPS": "60",
            "LoadedAreaLimit": "12",
        },
    }
    for section, values in defaults.items():
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in values.items():
            parser.set(section, key, value)

    os.makedirs(server.data["dir"], exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        parser.write(handle, space_around_delimiters=False)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Return to Moria server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Return to Moria server files and optionally restart the server."

restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Return to Moria server."


def prestart(server):
    """Refresh the managed dedicated-server config before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the UDP listener exposed by Return to Moria."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the same UDP endpoint used by ``query``."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Return to Moria server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"]]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=PREFER_PROTON,
        )
    return cmd, server.data["dir"]


def _find_linux_server_pids(server):
    """Return Linux-hosted Return to Moria server pids for *server*."""

    if not IS_LINUX:
        return []
    install_marker = os.path.basename(os.path.normpath(server.data.get("dir", "")))
    if not install_marker:
        return []
    try:
        output = subprocess.check_output(
            ["ps", "-eo", "pid=,args="],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    pids = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        pid_text, _sep, args = line.partition(" ")
        if not pid_text.isdigit():
            continue
        if "MoriaServer-Win64-Shipping.exe" not in args:
            continue
        if install_marker not in args:
            continue
        pids.append(int(pid_text))
    return pids


def do_stop(server, j):
    """Stop Return to Moria using an interrupt signal."""

    if IS_LINUX:
        pids = _find_linux_server_pids(server)
        for pid in pids:
            os.kill(pid, signal.SIGINT)
        if pids:
            return
    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Return to Moria status is not implemented yet."


def message(server, msg):
    """Return to Moria has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Return to Moria server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Return to Moria datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("advertiseaddress", "worldname", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=({"key": "port", "protocol": "udp"},),
    prefer_proton=PREFER_PROTON,
    extra_env=_container_runtime_env,
    stop_mode="exec-console",
    stdin_open=True,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=({"key": "port", "protocol": "udp"},),
    prefer_proton=PREFER_PROTON,
    extra_env=_container_runtime_env,
    stop_mode="exec-console",
    stdin_open=True,
    tty=True,
)
