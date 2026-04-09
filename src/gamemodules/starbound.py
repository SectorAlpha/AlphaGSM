"""Starbound dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 211820
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("DIR", "The directory to install Starbound in", str),
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
    "update": "Update the Starbound dedicated server to the latest version.",
    "restart": "Restart the Starbound dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="linux64/starbound_server"):
    """Collect and store configuration values for a Starbound server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("backupfiles", ["giraffe_storage", "linux64/sbboot.config"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {
                "default": {"targets": ["giraffe_storage", "linux64/sbboot.config"]}
            },
            "schedule": [("default", 0, "days")],
        }

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Starbound server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Starbound dedicated server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Starbound server files and optionally restart the server."""

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
    """Restart the Starbound server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Starbound dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return ["./" + server.data["exe_name"]], server.data["dir"]


def do_stop(server, j):
    """Send a shutdown command to Starbound."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed Starbound status is not implemented yet."""


def message(server, msg):
    """Starbound has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Starbound server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Starbound datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=(),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=(),
        stdin_open=True,
    )
