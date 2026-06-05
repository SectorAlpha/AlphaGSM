"""Dark and Light dedicated server lifecycle helpers."""

import os
import signal
import subprocess
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 630230
steam_anonymous_login_possible = True
DEFAULT_EXECUTABLE = "DNL/Binaries/Win64/DNLServer.exe"
ROOT_DIR_CANDIDATES = (
    "DNL Dedicated Server",
    os.path.join("steamapps", "common", "DNL Dedicated Server"),
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Dark and Light server",
    "The directory to install Dark and Light in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Dark and Light dedicated server to the latest version.",
    "Restart the Dark and Light dedicated server.",
)
command_functions = {}
setting_schema = {
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Server admin password.",
        secret=True,
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required to join the server.",
        secret=True,
    ),
}
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


def configure(server, ask, port=None, dir=None, *, exe_name=DEFAULT_EXECUTABLE):
    """Collect and store configuration values for a Dark and Light server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27016",
            "startmap": "DNL_ALL",
            "servername": "AlphaGSM %s" % (server.name,),
            "serverpassword": "",
            "adminpassword": "alphagsm",
            "maxplayers": "70",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DNL/Saved/Config/WindowsServer", "DNL/Saved/SavedArks"],
        targets=["DNL/Saved/Config/WindowsServer", "DNL/Saved/SavedArks"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Dark and Light server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _resolve_install_root(server):
    """Return the real Dark and Light content root for the current install tree."""

    configured_dir = server.data["dir"]
    candidates = [configured_dir]
    for relative_dir in ROOT_DIR_CANDIDATES:
        candidate = os.path.join(configured_dir, relative_dir)
        if candidate not in candidates:
            candidates.append(candidate)

    executable_candidates = [server.data.get("exe_name", DEFAULT_EXECUTABLE)]
    if DEFAULT_EXECUTABLE not in executable_candidates:
        executable_candidates.append(DEFAULT_EXECUTABLE)

    for candidate_dir in candidates:
        for executable in executable_candidates:
            if os.path.isfile(os.path.join(candidate_dir, executable)):
                return candidate_dir

    return configured_dir


def _resolve_executable(server):
    """Return ``(root_dir, executable)`` for the installed DNL payload."""

    executable_candidates = [server.data.get("exe_name", DEFAULT_EXECUTABLE)]
    if DEFAULT_EXECUTABLE not in executable_candidates:
        executable_candidates.append(DEFAULT_EXECUTABLE)
    root_dir = _resolve_install_root(server)
    for executable in executable_candidates:
        if os.path.isfile(os.path.join(root_dir, executable)):
            return root_dir, executable
    raise ServerError("Executable file not found")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Dark and Light server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Dark and Light server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Dark and Light server."


def get_query_address(server):
    """Return the live Dark and Light query endpoint.

    On Linux, the Wine/Proton-hosted dedicated server binds the game UDP port
    but does not expose a working A2S listener on ``queryport``. Use the game
    port's generic UDP health check there so query/info reflect the live
    runtime contract. Keep the historical A2S query-port mapping on non-Linux
    hosts.
    """

    host = runtime_module.resolve_query_host(server)
    if IS_LINUX:
        return (host, int(server.data["port"]), "udp")
    return (host, int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Dark and Light dedicated server."""

    root_dir, executable = _resolve_executable(server)
    exe_path = os.path.join(root_dir, executable)
    working_dir = os.path.dirname(exe_path) or root_dir
    map_arg = (
        "%s?listen?SessionName=%s?ServerPassword=%s?ServerAdminPassword=%s?Port=%s?QueryPort=%s?MaxPlayers=%s"
        % (
            server.data["startmap"],
            server.data["servername"],
            server.data["serverpassword"],
            server.data["adminpassword"],
            server.data["port"],
            server.data["queryport"],
            server.data["maxplayers"],
        )
    )
    cmd = [
        os.path.basename(executable),
        map_arg,
        "-nullRHI",
        "-log",
        "-unattended",
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, working_dir


def _find_linux_server_pids(server):
    """Return live Linux-hosted DNLServer.exe pids for *server*."""

    port = server.data.get("port")
    queryport = server.data.get("queryport")
    if port is None or queryport is None:
        return []
    markers = (
        server.data.get("exe_name", "DNL/Binaries/Win64/DNLServer.exe"),
        "Port=%s" % (port,),
        "QueryPort=%s" % (queryport,),
    )
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
        if all(marker in args for marker in markers):
            pids.append(int(pid_text))
    return pids


def do_stop(server, j):
    """Stop Dark and Light, targeting the real server process on Linux."""

    if IS_LINUX:
        pids = _find_linux_server_pids(server)
        for pid in pids:
            os.kill(pid, signal.SIGTERM)
        if pids:
            return
    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Dark and Light status is not implemented yet."""


def message(server, msg):
    """Dark and Light has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Dark and Light server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Dark and Light datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("startmap", "servername", "serverpassword", "adminpassword", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    extra_env=_container_runtime_env,
)
