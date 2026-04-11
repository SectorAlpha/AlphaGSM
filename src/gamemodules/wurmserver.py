"""Wurm Unlimited dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 402370
steam_anonymous_login_possible = True

DEFAULT_LAUNCH_CONFIG = """[Runtime]
OverrideDefaultJavaPath=false
JavaPath=
[Memory]
InitialHeap=512m
MaxHeapSize=2048m
[Utility]
CleanLogsOnStart=true
[VMParams]
JvmParam0=-XX:+AggressiveOpts
"""

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Wurm Unlimited in", str),
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
    "update": "Update the Wurm Unlimited dedicated server to the latest version.",
    "restart": "Restart the Wurm Unlimited dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def _parse_port(value):
    """Parse a Wurm port value constrained to Java's signed short range."""

    port = int(value)
    if not 1 <= port <= 32767:
        raise ServerError("Port must be between 1 and 32767 for Wurm")
    return port


def configure(server, ask, port=None, dir=None, *, exe_name="WurmServerLauncher"):
    """Collect and store configuration values for a Wurm Unlimited server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("worldname", "Adventure")
    server.data.setdefault("queryport", 27016)
    server.data.setdefault("internalport", 7220)
    server.data.setdefault("rmiport", 7221)
    server.data.setdefault("backupfiles", ["Adventure", "Creative", "WurmServerLauncher"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Adventure", "Creative"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 3724)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Wurm Unlimited server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Wurm Unlimited server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )
    steamclient_src = os.path.join(server.data["dir"], "linux64", "steamclient.so")
    steamclient_dst = os.path.join(server.data["dir"], "nativelibs", "steamclient.so")
    launch_config = os.path.join(server.data["dir"], "LaunchConfig.ini")
    if os.path.isfile(steamclient_src):
        os.makedirs(os.path.dirname(steamclient_dst), exist_ok=True)
        with open(steamclient_src, "rb") as src_file, open(steamclient_dst, "wb") as dst_file:
            dst_file.write(src_file.read())
    if not os.path.isfile(launch_config):
        with open(launch_config, "w", encoding="utf-8") as launch_config_file:
            launch_config_file.write(DEFAULT_LAUNCH_CONFIG)
    for world_name in ("Adventure", "Creative"):
        bundled_world = os.path.join(server.data["dir"], "dist", world_name)
        install_world = os.path.join(server.data["dir"], world_name)
        if os.path.isdir(bundled_world) and not os.path.exists(install_world):
            shutil.copytree(bundled_world, install_world)


def update(server, validate=False, restart=False):
    """Update the Wurm Unlimited server files and optionally restart the server."""

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
    """Restart the Wurm Unlimited server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Wurm Unlimited dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "start=%s" % (server.data["worldname"],),
            "ip=127.0.0.1",
            "externalport=%s" % (server.data["port"],),
            "queryport=%s" % (server.data["queryport"],),
            "rmiregport=%s" % (server.data["internalport"],),
            "rmiport=%s" % (server.data["rmiport"],),
            "servername=%s" % (server.data["servername"],),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the TCP endpoint used for generic Wurm reachability checks."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")


def get_info_address(server):
    """Return the TCP endpoint used for generic Wurm info output."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Wurm Unlimited using the standard shutdown command."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed Wurm Unlimited status is not implemented yet."""


def message(server, msg):
    """Wurm Unlimited has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Wurm Unlimited server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Wurm Unlimited datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport", "internalport", "rmiport"):
        return _parse_port(value[0])
    if key[0] in ("servername", "exe_name", "dir", "worldname"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'internalport', 'protocol': 'udp'}, {'key': 'internalport', 'protocol': 'tcp'}, {'key': 'rmiport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'internalport', 'protocol': 'udp'}, {'key': 'internalport', 'protocol': 'tcp'}, {'key': 'rmiport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
    )
