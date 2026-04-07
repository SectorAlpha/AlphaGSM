"""Insurgency: Sandstorm dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

steam_app_id = 581330
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Insurgency: Sandstorm in", str),
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
    "update": "Update the Insurgency: Sandstorm dedicated server to the latest version.",
    "restart": "Restart the Insurgency: Sandstorm dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Insurgency/Binaries/Linux/InsurgencyServer-Linux-Shipping"):
    """Collect and store configuration values for an Insurgency: Sandstorm server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("mapcycle", "Scenario_Crossing_Push_Security")
    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("maxplayers", "28")
    server.data.setdefault("gslt", "")
    server.data.setdefault("backupfiles", ["Insurgency/Config/Server", "Insurgency/Saved"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Insurgency/Config/Server", "Insurgency/Saved"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27102)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    server.data.setdefault("queryport", str(int(server.data["port"]) + 1))

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Insurgency: Sandstorm server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Insurgency: Sandstorm server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Insurgency: Sandstorm server files and optionally restart the server."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(server.data["dir"], steam_app_id, steam_anonymous_login_possible, validate=validate)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def restart(server):
    """Restart the Insurgency: Sandstorm server."""

    server.stop()
    server.start()


def get_query_address(server):
    """Insurgency: Sandstorm uses Steam A2S on the dedicated query port."""
    return ("127.0.0.1", int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""
    return ("127.0.0.1", int(server.data["queryport"]), "a2s")


def get_start_command(server):
    """Build the command used to launch an Insurgency: Sandstorm server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        "./" + server.data["exe_name"],
        "%s?MaxPlayers=%s" % (server.data["mapcycle"], server.data["maxplayers"]),
        "-Port=%s" % (server.data["port"],),
        "-QueryPort=%s" % (server.data["queryport"],),
        "-hostname=%s" % (server.data["hostname"],),
        "-log",
    ]
    if server.data.get("gslt"):
        cmd.append("-GSLTToken=%s" % (server.data["gslt"],))
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Insurgency: Sandstorm by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Insurgency: Sandstorm status is not implemented yet."""


def message(server, msg):
    """Insurgency: Sandstorm has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an Insurgency: Sandstorm server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Insurgency: Sandstorm datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "maxplayers"):
        return int(value[0])
    if key[0] in ("mapcycle", "hostname", "gslt", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")
