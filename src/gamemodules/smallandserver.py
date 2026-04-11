"""Smalland dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 808040
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Smalland server", int),
            ArgSpec("DIR", "The directory to install Smalland in", str),
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
    "update": "Update the Smalland dedicated server to the latest version.",
    "restart": "Restart the Smalland dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def _build_launch_args(server):
    """Build the Smalland world and runtime arguments passed to the UE server."""

    world_arg = (
        '/Game/Maps/WorldGame/WorldGame_Smalland'
        '?SERVERNAME="%s"'
        '?WORLDNAME="%s"'
        % (server.data["servername"], server.data["worldname"])
    )
    if server.data.get("serverpassword"):
        world_arg += '?PASSWORD="%s"' % (server.data["serverpassword"],)
    world_arg += "?CROSSPLAY"
    world_arg += "?lengthofdayseconds=1800"
    world_arg += "?lengthofseasonseconds=10800"
    world_arg += "?creaturehealthmodifier=100"
    world_arg += "?creaturedamagemodifier=100"
    world_arg += "?creaturerespawnratemodifier=100"
    world_arg += "?resourcerespawnratemodifier=100"
    world_arg += "?creaturespawnchancemodifier=100"
    world_arg += "?craftingtimemodifier=100"
    world_arg += "?craftingfuelmodifier=100"
    world_arg += "?stormfrequencymodifier=100"
    world_arg += "?nourishmentlossmodifier=100"
    world_arg += "?falldamagemodifier=100"
    world_arg += "?SESSIONPLATFORM=pc"
    return [
        world_arg,
        "-ini:Engine:[EpicOnlineServices]:DeploymentId=50f2b148496e4cbbbdeefbecc2ccd6a3",
        "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientId=xyza78918KT08TkA6emolUay8yhvAAy2",
        "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientSecret=aN2GtVw7aHb6hx66HwohNM+qktFaO3vtrLSbGdTzZWk",
        "-port=%s" % (server.data["port"],),
        "-NOSTEAM",
        "-log",
    ]


def configure(server, ask, port=None, dir=None, *, exe_name="SMALLANDServer.sh"):
    """Collect and store configuration values for a Smalland server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("worldname", "World")
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("serverpassword", "")
    server.data.setdefault("backupfiles", ["Saved", "Config"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Saved", "Config"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 7777)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Smalland server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Smalland server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )
    for script_name in ("start-server.sh", "SMALLANDServer.sh"):
        script_path = os.path.join(server.data["dir"], script_name)
        if os.path.isfile(script_path):
            os.chmod(script_path, os.stat(script_path).st_mode | 0o111)


def update(server, validate=False, restart=False):
    """Update the Smalland server files and optionally restart the server."""

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
    """Restart the Smalland server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Smalland dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], *_build_launch_args(server)],
        server.data["dir"],
    )


def get_query_address(server):
    """Smalland exposes a silent UDP listener on the main game port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Smalland's info surface is the same UDP listener as its query surface."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Smalland using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Smalland status is not implemented yet."""


def message(server, msg):
    """Smalland has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Smalland server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Smalland datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "queryport"):
        return int(value[0])
    if key[0] in ("servername", "worldname", "serverpassword", "exe_name", "dir"):
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
