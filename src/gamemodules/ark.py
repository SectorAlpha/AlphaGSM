"""ARK: Survival Evolved dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 376030
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the ARK server", int),
            ArgSpec("DIR", "The directory to install ARK in", str),
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
    "update": "Update the ARK: Survival Evolved dedicated server to the latest version.",
    "restart": "Restart the ARK: Survival Evolved dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="ShooterGame/Binaries/Linux/ShooterGameServer",
):
    """Collect and store configuration values for an ARK server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("map", "TheIsland")
    server.data.setdefault("sessionname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("adminpassword", "alphagsm")
    server.data.setdefault("serverpassword", "")
    server.data.setdefault("maxplayers", "70")
    server.data.setdefault("queryport", "27015")
    server.data.setdefault(
        "backupfiles",
        ["ShooterGame/Saved", "ShooterGame/Saved/Config/LinuxServer"],
    )
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["ShooterGame/Saved"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 7777)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the ARK server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the ARK server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the ARK server files and optionally restart the server."""

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
    """Restart the ARK server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch an ARK dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    map_args = (
        "%s?listen?SessionName=%s?Port=%s?QueryPort=%s?MaxPlayers=%s?ServerAdminPassword=%s"
        % (
            server.data["map"],
            server.data["sessionname"],
            server.data["port"],
            server.data["queryport"],
            server.data["maxplayers"],
            server.data["adminpassword"],
        )
    )
    if server.data["serverpassword"]:
        map_args += "?ServerPassword=%s" % (server.data["serverpassword"],)
    return (
        ["./" + server.data["exe_name"], map_args, "-server", "-log"],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send the standard quit command to ARK."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed ARK status is not implemented yet."""


def message(server, msg):
    """ARK has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ARK server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ARK datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("map", "sessionname", "adminpassword", "serverpassword", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
