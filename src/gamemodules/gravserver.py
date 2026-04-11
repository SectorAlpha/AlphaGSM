"""GRAV dedicated server lifecycle helpers using owned game files."""

import os

import screen
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

import server.runtime as runtime_module

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the GRAV server", int),
            ArgSpec("DIR", "The directory containing the GRAV server files", str),
        )
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="CAGGameServer-Win32-Shipping"):
    """Collect and store configuration values for a GRAV server."""

    server.data.setdefault("peerport", "7778")
    server.data.setdefault("queryport", "27015")
    server.data.setdefault("maxplayers", "32")
    server.data.setdefault("servername", server.name)
    server.data.setdefault("adminpassword", "")
    server.data.setdefault("backupfiles", ["CAGGame", "Cloud"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["CAGGame", "Cloud"]}},
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
            inp = input("Where are the GRAV server files located: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """GRAV uses user-provided files; ensure the install directory exists."""

    os.makedirs(server.data["dir"], exist_ok=True)


def get_start_command(server):
    """Build the command used to launch a GRAV dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            'brokerstart?NumHomePlanets=1?AdminPassword=%s?PlanetManagerName="defaultmetaverse"?PlanetPortOffset=0?steamsockets?Port=%s?PeerPort=%s?QueryPort=%s?MaxPlayers=%s?CloudDir="CharacterSaveData"?ServerName="%s"?SteamDontAdvertise=0?AllowPVP=1?DoBaseDecay=1'
            % (
                server.data["adminpassword"],
                server.data["port"],
                server.data["peerport"],
                server.data["queryport"],
                server.data["maxplayers"],
                server.data["servername"],
            ),
            "-seekfreeloadingserver",
            "-unattended",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop GRAV by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed GRAV status is not implemented yet."""


def message(server, msg):
    """GRAV has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a GRAV server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported GRAV datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "peerport", "queryport", "maxplayers"):
        return int(value[0])
    if key[0] in ("exe_name", "dir", "servername", "adminpassword"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'peerport', 'protocol': 'udp'}, {'key': 'peerport', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'peerport', 'protocol': 'udp'}, {'key': 'peerport', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
    )
