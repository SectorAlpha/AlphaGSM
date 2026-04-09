"""Rust dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 258550
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Rust server", int),
            ArgSpec("DIR", "The directory to install Rust in", str),
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
    "update": "Update the Rust dedicated server to the latest version.",
    "restart": "Restart the Rust dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="RustDedicated"):
    """Collect and store configuration values for a Rust server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("level", "Procedural Map")
    server.data.setdefault("worldsize", "3000")
    server.data.setdefault("maxplayers", "50")
    server.data.setdefault("seed", "12345")
    server.data.setdefault("rconport", "28016")
    server.data.setdefault("backupfiles", ["server", "oxide", "RustDedicated_Data"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["server"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 28015)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Rust server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Rust server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Rust server files and optionally restart the server."""

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
    """Restart the Rust server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Rust dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-batchmode",
            "+server.ip",
            "0.0.0.0",
            "+server.port",
            str(server.data["port"]),
            "+server.hostname",
            server.data["hostname"],
            "+server.level",
            server.data["level"],
            "+server.worldsize",
            str(server.data["worldsize"]),
            "+server.maxplayers",
            str(server.data["maxplayers"]),
            "+server.seed",
            str(server.data["seed"]),
            "+rcon.ip",
            "0.0.0.0",
            "+rcon.port",
            str(server.data["rconport"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send the standard quit command to Rust."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed Rust status is not implemented yet."""


def message(server, msg):
    """Rust has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Rust server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Rust datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "worldsize", "maxplayers", "seed", "rconport"):
        return int(value[0])
    if key[0] in ("hostname", "level", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'rconport', 'protocol': 'udp'}, {'key': 'rconport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'rconport', 'protocol': 'udp'}, {'key': 'rconport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
    )
