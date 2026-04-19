"""7 Days to Die dedicated server lifecycle helpers."""

import os
import re

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 294420
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the 7 Days to Die server", int),
            ArgSpec("DIR", "The directory to install 7 Days to Die in", str),
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
    "update": "Update the 7 Days to Die dedicated server to the latest version.",
    "restart": "Restart the 7 Days to Die dedicated server.",
}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port",)


def configure(server, ask, port=None, dir=None, *, exe_name="startserver.sh"):
    """Collect and store configuration values for a 7 Days to Die server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("configfile", "serverconfig.xml")
    server.data.setdefault("backupfiles", ["Saves", "serverconfig.xml", "startserver.sh"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Saves", "serverconfig.xml"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 26900)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the 7 Days to Die server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def sync_server_config(server):
    """Update the ServerPort entry in serverconfig.xml to match server.data."""
    port = server.data.get("port")
    if port is None:
        return
    configfile = server.data.get("configfile", "serverconfig.xml")
    config_path = os.path.join(server.data["dir"], configfile)
    if not os.path.isfile(config_path):
        return
    with open(config_path, encoding="utf-8") as fh:
        content = fh.read()
    new_content = re.sub(
        r'(<property\s+name="ServerPort"\s+value=")[^"]*(")'
        , r'\g<1>' + str(port) + r'\2',
        content,
    )
    if new_content != content:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)


def install(server):
    """Download the 7 Days to Die server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )
    sync_server_config(server)


def update(server, validate=False, restart=False):
    """Update the 7 Days to Die server files and optionally restart the server."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(server.data["dir"], steam_app_id, steam_anonymous_login_possible, validate=validate)
    sync_server_config(server)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def prestart(server, *args, **kwargs):
    """Refresh serverconfig.xml from the current datastore before launch."""

    sync_server_config(server)


def restart(server):
    """Restart the 7 Days to Die server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a 7 Days to Die dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "-configfile=%s" % (server.data["configfile"],)],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send the standard shutdown command to 7 Days to Die."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed 7 Days to Die status is not implemented yet."""


def message(server, msg):
    """7 Days to Die has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a 7 Days to Die server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported 7 Days to Die datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("configfile", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
