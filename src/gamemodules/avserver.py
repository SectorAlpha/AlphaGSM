"""Avorion dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 565060
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Avorion in", str),
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
    "update": "Update the Avorion dedicated server to the latest version.",
    "restart": "Restart the Avorion dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="server.sh"):
    """Collect and store configuration values for an Avorion server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("galaxy", server.name)
    server.data.setdefault("seed", "AlphaGSM")
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("administration", "")
    server.data.setdefault("backupfiles", ["galaxies", "server.sh"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["galaxies"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27000)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    server.data.setdefault("queryport", int(server.data["port"]) + 3)
    server.data.setdefault("steamqueryport", int(server.data["port"]) + 20)
    server.data.setdefault("steammasterport", int(server.data["port"]) + 21)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Avorion server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Avorion server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Avorion server files and optionally restart the server."""

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
    """Restart the Avorion server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch an Avorion dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "--datapath",
        "./galaxies",
        "--galaxy-name",
        server.data["galaxy"],
        "--server-name",
        server.data["servername"],
        "--port",
        str(server.data["port"]),
        "--query-port",
        str(server.data["queryport"]),
        "--steam-query-port",
        str(server.data["steamqueryport"]),
        "--steam-master-port",
        str(server.data["steammasterport"]),
        "--seed",
        server.data["seed"],
    ]
    if server.data.get("administration"):
        command.extend(["--admin", server.data["administration"]])
    return (command, server.data["dir"])


def get_query_address(server):
    """Return the UDP endpoint used for Avorion reachability checks."""

    return (runtime_module.resolve_query_host(server), int(server.data["steamqueryport"]), "udp")


def get_info_address(server):
    """Return the UDP endpoint used for Avorion info output."""

    return get_query_address(server)
    return get_query_address(server)


def do_stop(server, j):
    """Stop Avorion using the standard stop command."""

    screen.send_to_server(server.name, "\nstop\n")


def status(server, verbose):
    """Detailed Avorion status is not implemented yet."""


def message(server, msg):
    """Avorion has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an Avorion server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Avorion datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "steamqueryport", "steammasterport"):
        return int(value[0])
    if key[0] in ("galaxy", "seed", "administration", "servername", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'steamqueryport', 'protocol': 'udp'}, {'key': 'steamqueryport', 'protocol': 'tcp'}, {'key': 'steammasterport', 'protocol': 'udp'}, {'key': 'steammasterport', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'steamqueryport', 'protocol': 'udp'}, {'key': 'steamqueryport', 'protocol': 'tcp'}, {'key': 'steammasterport', 'protocol': 'udp'}, {'key': 'steammasterport', 'protocol': 'tcp'}),
        stdin_open=True,
    )
