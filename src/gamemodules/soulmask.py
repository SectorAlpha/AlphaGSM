"""Soulmask dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

steam_app_id = 3017300
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Soulmask server", int),
            ArgSpec("DIR", "The directory to install Soulmask in", str),
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
    "update": "Update the Soulmask dedicated server to the latest version.",
    "restart": "Restart the Soulmask dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="WSServer.sh"):
    """Collect and store configuration values for a Soulmask server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("queryport", "27015")
    server.data.setdefault("echoport", "18888")
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("level", "Level01_Main")
    server.data.setdefault("adminpassword", "alphagsm")
    server.data.setdefault("serverpassword", "")
    server.data.setdefault("maxplayers", "10")
    server.data.setdefault("bindaddress", "0.0.0.0")
    server.data.setdefault("backupinterval", "900")
    server.data.setdefault("savinginterval", "600")
    server.data.setdefault("mods", "")
    server.data.setdefault("backupfiles", ["WS/Saved"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["WS/Saved"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 8777)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Soulmask server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Soulmask server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Soulmask server files and optionally restart the server."""

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
    """Restart the Soulmask server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Soulmask dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        server.data["level"],
        "-server",
        "-log",
        "-forcepassthrough",
        "-UTF8Output",
        "-SteamServerName=%s" % (server.data["servername"],),
        "-MaxPlayers=%s" % (server.data["maxplayers"],),
        "-PSW=%s" % (server.data["serverpassword"],),
        "-adminpsw=%s" % (server.data["adminpassword"],),
        "-MULTIHOME=%s" % (server.data["bindaddress"],),
        "-Port=%s" % (server.data["port"],),
        "-QueryPort=%s" % (server.data["queryport"],),
        "-EchoPort=%s" % (server.data["echoport"],),
        "-saving=%s" % (server.data["savinginterval"],),
        "-backup=%s" % (server.data["backupinterval"],),
    ]
    if server.data["mods"]:
        command.append('-mod="%s"' % (server.data["mods"],))
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Soulmask using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Soulmask status is not implemented yet."""


def message(server, msg):
    """Soulmask has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Soulmask server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Soulmask datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "echoport", "maxplayers", "backupinterval", "savinginterval"):
        return int(value[0])
    if key[0] in (
        "servername",
        "level",
        "adminpassword",
        "serverpassword",
        "bindaddress",
        "mods",
        "exe_name",
        "dir",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")
