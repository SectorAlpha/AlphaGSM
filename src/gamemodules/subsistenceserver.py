"""Subsistence dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module

steam_app_id = 1362640
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Subsistence server", int),
            ArgSpec("DIR", "The directory to install Subsistence in", str),
        )
    ),
    "update": CmdSpec(
        options=(
            OptSpec("v", ["validate"], "Validate the server files after updating", "validate", None, True),
            OptSpec("r", ["restart"], "Restart the server after updating", "restart", None, True),
        )
    ),
    "restart": CmdSpec(),
}
command_descriptions = {
    "update": "Update the Subsistence dedicated server to the latest version.",
    "restart": "Restart the Subsistence dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Win32/Subsistence.exe"):
    """Collect and store configuration values for a Subsistence server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("queryport", "27016")
    server.data.setdefault("maxplayers", "10")
    server.data.setdefault("backupfiles", ["ServerData", "Binaries/Win32"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["ServerData"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27015)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Subsistence server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Subsistence server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
        force_windows=IS_LINUX,
    )


def update(server, validate=False, restart=False):
    """Update the Subsistence server files and optionally restart the server."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(server.data["dir"], steam_app_id, steam_anonymous_login_possible, validate=validate, force_windows=IS_LINUX)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def restart(server):
    """Restart the Subsistence server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Subsistence dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    # The bat file shipped with the server uses 'start /B Subsistence.exe server coldmap1'
    # which fails under Wine (ShellExecuteEx not supported).  We run Subsistence.exe
    # directly with the same UDK URL arguments inlined into the map string.
    port = server.data.get("port", 27015)
    queryport = server.data.get("queryport", 27016)
    maxplayers = server.data.get("maxplayers", 10)
    map_url = (
        f"server coldmap1?Port={port}?QueryPort={queryport}"
        f"?MaxPlayers={maxplayers}?steamsockets"
    )
    # Work from the exe's own directory so DLL loading succeeds.
    # Use the basename only (no path prefix) because cwd is already the exe dir.
    binaries_dir = os.path.join(server.data["dir"], "Binaries", "Win32")
    # -log writes UE3 engine output to UDKGame/Logs/Launch.log instead of a
    # Window owned by the process.  LIBGL_ALWAYS_SOFTWARE forces Mesa software
    # rendering so that wined3d SM3 shader compilation never hits GPU driver
    # issues that crash UE3 combined client/server binaries under Wine.
    cmd = ["Subsistence.exe", map_url, "-log"]
    if IS_LINUX:
        wine_cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
        # Inject software-renderer env var after any existing env prefix so that
        # Wine uses Mesa/llvmpipe instead of the GPU, preventing D3D SM3 shader
        # compilation failures.
        if wine_cmd and wine_cmd[0] == "env":
            wine_cmd.insert(1, "LIBGL_ALWAYS_SOFTWARE=1")
        else:
            wine_cmd = ["env", "LIBGL_ALWAYS_SOFTWARE=1"] + wine_cmd
        cmd = wine_cmd
    return cmd, binaries_dir


def do_stop(server, j):
    """Stop Subsistence using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Subsistence status is not implemented yet."""


def message(server, msg):
    """Subsistence has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Subsistence server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Subsistence datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "maxplayers"):
        return int(value[0])
    if key[0] in ("exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return proton.get_runtime_requirements(
        server,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return proton.get_container_spec(
        server,
        get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )
