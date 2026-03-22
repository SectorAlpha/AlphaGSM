"""Mumble server lifecycle helpers."""

import os
import shutil

import screen
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to store Mumble server files in", str),
        )
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _default_executable():
    """Return the preferred Mumble server executable name."""

    return shutil.which("mumble-server") or shutil.which("murmurd") or "mumble-server"


def _config_path(server):
    """Return the path to the managed Mumble configuration file."""

    return os.path.join(server.data["dir"], "mumble-server.ini")


def _write_config(server):
    """Write a minimal Mumble configuration file if one is missing."""

    config_path = _config_path(server)
    if os.path.isfile(config_path):
        return
    with open(config_path, "w") as config_file:
        config_file.write("welcometext=%s\n" % (server.data["welcometext"],))
        config_file.write("port=%s\n" % (server.data["port"],))
        config_file.write("users=%s\n" % (server.data["users"],))
        config_file.write("database=%s\n" % (server.data["database"],))
        if server.data.get("serverpassword"):
            config_file.write("serverpassword=%s\n" % (server.data["serverpassword"],))


def configure(server, ask, port=None, dir=None, *, exe_name=None):
    """Collect and store configuration values for a Mumble server."""

    server.data.setdefault("welcometext", "Welcome to %s" % (server.name,))
    server.data.setdefault("users", "100")
    server.data.setdefault("database", "mumble-server.sqlite")
    server.data.setdefault("serverpassword", "")
    server.data.setdefault("backupfiles", ["mumble-server.ini", "mumble-server.sqlite"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["mumble-server.ini", "mumble-server.sqlite"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 64738)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to store the Mumble server files: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name or _default_executable())
    server.data.save()
    return (), {}


def install(server):
    """Prepare the local filesystem for a Mumble server."""

    os.makedirs(server.data["dir"], exist_ok=True)
    _write_config(server)
    server.data.save()


def get_start_command(server):
    """Build the command used to launch a Mumble server."""

    return (
        [
            server.data["exe_name"],
            "-fg",
            "-ini",
            _config_path(server),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Mumble by sending an interrupt to the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Mumble status is not implemented yet."""


def message(server, msg):
    """Mumble has no generic broadcast console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Mumble server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Mumble datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("welcometext", "users", "database", "serverpassword", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")
