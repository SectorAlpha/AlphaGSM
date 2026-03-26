"""Aloft dedicated server lifecycle helpers using owned game files."""

import os

import screen
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The server port to use for the Aloft server", int),
            ArgSpec("DIR", "The directory containing the Aloft server files", str),
        )
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="AloftServerNoGuiLoad.ps1"):
    """Collect and store configuration values for an Aloft server."""

    server.data.setdefault("mapname", server.name)
    server.data.setdefault("servername", server.name)
    server.data.setdefault("visible", "true")
    server.data.setdefault("privateislands", "false")
    server.data.setdefault("playercount", "8")
    server.data.setdefault("backupfiles", ["output.log", "ServerRoomCode.txt", "Saves"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["output.log", "ServerRoomCode.txt", "Saves"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 0)
    if ask:
        inp = input("Please specify the server port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where are the Aloft server files located: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Aloft uses user-provided files; ensure the install directory exists."""

    os.makedirs(server.data["dir"], exist_ok=True)


def get_start_command(server):
    """Build the command used to launch an Aloft dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "pwsh",
            "./" + server.data["exe_name"],
            "-batchmode",
            "-nographics",
            "-server",
            "load#%s#" % (server.data["mapname"],),
            "servername#%s#" % (server.data["servername"],),
            "log#ERROR#",
            "isvisible#%s#" % (server.data["visible"],),
            "privateislands#%s#" % (server.data["privateislands"],),
            "playercount#%s#" % (server.data["playercount"],),
            "serverport#%s#" % (server.data["port"],),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Aloft by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Aloft status is not implemented yet."""


def message(server, msg):
    """Aloft has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an Aloft server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Aloft datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "playercount"):
        return int(value[0])
    if key[0] in ("exe_name", "dir", "mapname", "servername", "visible", "privateislands"):
        return str(value[0])
    raise ServerError("Unsupported key")
