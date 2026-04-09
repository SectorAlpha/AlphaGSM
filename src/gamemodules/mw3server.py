"""Call of Duty: Modern Warfare 3 dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module

steam_app_id = 115310
steam_anonymous_login_possible = False

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Modern Warfare 3 server", int),
            ArgSpec("DIR", "The directory to install Modern Warfare 3 in", str),
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
    "update": "Update the Modern Warfare 3 dedicated server to the latest version.",
    "restart": "Restart the Modern Warfare 3 dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="iw5mp_server.exe"):
    """Collect and store configuration values for a Modern Warfare 3 server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("startmap", "mp_alpha")
    server.data.setdefault("maxplayers", "18")
    server.data.setdefault("backupfiles", ["main", "players2", "zone"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["main", "players2", "zone"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27016)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Modern Warfare 3 server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Modern Warfare 3 server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
        force_windows=IS_LINUX,
    )


def update(server, validate=False, restart=False):
    """Update the Modern Warfare 3 server files and optionally restart the server."""

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
    """Restart the Modern Warfare 3 server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Modern Warfare 3 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
            server.data["exe_name"],
            "+set",
            "sv_hostname",
            server.data["hostname"],
            "+set",
            "net_port",
            str(server.data["port"]),
            "+set",
            "sv_maxclients",
            str(server.data["maxplayers"]),
            "+map",
            server.data["startmap"],
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Modern Warfare 3 by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Modern Warfare 3 status is not implemented yet."""


def message(server, msg):
    """Modern Warfare 3 has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Modern Warfare 3 server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Modern Warfare 3 datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "maxplayers"):
        return int(value[0])
    if key[0] in ("hostname", "startmap", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return proton.get_runtime_requirements(
        server,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return proton.get_container_spec(
        server,
        get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )
