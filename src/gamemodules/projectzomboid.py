"""Project Zomboid dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 380870
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The default game port to store for this server", int),
            ArgSpec("DIR", "The directory to install Project Zomboid in", str),
        )
    ),
    "update": CmdSpec(
        options=(
            OptSpec(
                "v",
                ["validate"],
                "Validate the server files after updating",
                "validate",
                None,
                True,
            ),
            OptSpec(
                "r",
                ["restart"],
                "Restart the server after updating",
                "restart",
                None,
                True,
            ),
        )
    ),
    "restart": CmdSpec(),
}
command_descriptions = {
    "update": "Update the Project Zomboid dedicated server to the latest version.",
    "restart": "Restart the Project Zomboid dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="start-server.sh"):
    """Collect and store configuration values for a Project Zomboid server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("servername", server.name)
    server.data.setdefault("adminpassword", "alphagsm")
    server.data.setdefault("backupfiles", ["Zomboid", "Server", "start-server.sh"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Zomboid", "Server"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 16261)
    if ask:
        inp = input(
            "Please specify the port to use for this server: [%s] " % (port,)
        ).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    # Build 41 dedicated servers expose their direct-connection listener on the
    # fixed UDP port configured in SERVERNAME.ini. Without module-managed config
    # files this remains the upstream default 16262.
    server.data.setdefault("queryport", 16262)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Project Zomboid server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Project Zomboid server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Project Zomboid server files and optionally restart."""

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
    """Restart the Project Zomboid server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Project Zomboid dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-servername",
            str(server.data["servername"]),
            "-adminpassword",
            str(server.data["adminpassword"]),
            "-port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", 16262)), "udp")


def get_info_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return get_query_address(server)


def do_stop(server, j):
    """Send the standard quit command to Project Zomboid."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed Project Zomboid status is not implemented yet."""


def message(server, msg):
    """Project Zomboid has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Project Zomboid server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Project Zomboid datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport"):
        return int(value[0])
    if key[0] in ("servername", "adminpassword", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
    )
