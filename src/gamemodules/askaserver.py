"""ASKA dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

from utils.platform_info import IS_LINUX

steam_app_id = 3246670
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the ASKA server", int),
            ArgSpec("DIR", "The directory to install ASKA in", str),
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
    "update": "Update the ASKA dedicated server to the latest version.",
    "restart": "Restart the ASKA dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="AskaServer.exe"):
    """Collect and store configuration values for an ASKA server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("servername", server.name)
    server.data.setdefault("displayname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("password", "")
    server.data.setdefault("maxplayers", "4")
    server.data.setdefault("queryport", "27016")
    server.data.setdefault("backupfiles", ["SaveGames", "ServerConfig"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["SaveGames", "ServerConfig"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27015)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the ASKA server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the ASKA server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
        force_windows=IS_LINUX,
    )


def update(server, validate=False, restart=False):
    """Update the ASKA server files and optionally restart the server."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        validate=validate,
    )
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def restart(server):
    """Restart the ASKA server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch an ASKA dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        server.data["exe_name"],
        "-batchmode",
        "-nographics",
        "-logFile",
        "./server.log",
        "-Port",
        str(server.data["port"]),
        "-QueryPort",
        str(server.data["queryport"]),
        "-ServerName",
        server.data["servername"],
        "-DisplayName",
        server.data["displayname"],
        "-MaxPlayers",
        str(server.data["maxplayers"]),
    ]
    if server.data["password"]:
        command.extend(["-Password", server.data["password"]])
    if IS_LINUX:
        command = proton.wrap_command(
            command, wineprefix=server.data.get("wineprefix")
        )
    return (command, server.data["dir"])


def get_runtime_requirements(server):
    """Return Docker runtime metadata for Wine/Proton-backed servers."""

    return proton.get_runtime_requirements(
        server,
        port_definitions=(("port", "udp"), ("queryport", "udp")),
    )


def get_container_spec(server):
    """Return the Docker launch spec for ASKA."""

    return proton.get_container_spec(
        server,
        get_start_command,
        port_definitions=(("port", "udp"), ("queryport", "udp")),
    )


def do_stop(server, j):
    """Stop the ASKA server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed ASKA status is not implemented yet."""


def message(server, msg):
    """ASKA has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an ASKA server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported ASKA datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "maxplayers"):
        return int(value[0])
    if key[0] in ("servername", "displayname", "password", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")
