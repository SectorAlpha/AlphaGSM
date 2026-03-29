"""Palworld dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

steam_app_id = 2394010
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port to use for the Palworld server", int),
            ArgSpec("DIR", "The directory to install Palworld in", str),
        ),
        options=(
            OptSpec(
                "c",
                ["community"],
                "Start the server in community server mode.",
                "publiclobby",
                None,
                True,
            ),
        ),
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
    "update": "Update the Palworld dedicated server to the latest version.",
    "restart": "Restart the Palworld dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="PalServer.sh", publiclobby=False):
    """Collect and store configuration values for a Palworld server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("queryport", "27015")
    server.data.setdefault("publiclobby", bool(publiclobby))
    server.data.setdefault("backupfiles", ["Pal/Saved", "PalWorldSettings.ini", "PalServer.sh"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Pal/Saved"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 8211)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Palworld server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def _settings_paths(server):
    """Return the default and active Palworld settings paths."""

    base_dir = os.path.join(server.data["dir"], "Pal", "Saved", "Config", "LinuxServer")
    return (
        os.path.join(server.data["dir"], "DefaultPalWorldSettings.ini"),
        os.path.join(base_dir, "PalWorldSettings.ini"),
    )


def install(server):
    """Download the Palworld server files and prepare the settings file."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )

    default_settings, active_settings = _settings_paths(server)
    active_dir = os.path.dirname(active_settings)
    if not os.path.isdir(active_dir):
        os.makedirs(active_dir)
    if os.path.isfile(default_settings) and not os.path.isfile(active_settings):
        shutil.copy2(default_settings, active_settings)


def update(server, validate=False, restart=False):
    """Update the Palworld server files and optionally restart the server."""

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
    """Restart the Palworld server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Palworld dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        "./" + server.data["exe_name"],
        "-port=%s" % (server.data["port"],),
        "-queryport=%s" % (server.data["queryport"],),
    ]
    if server.data.get("publiclobby"):
        cmd.append("-publiclobby")
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Send the standard shutdown command to Palworld."""

    screen.send_to_server(server.name, "\nShutdown 1\n")


def status(server, verbose):
    """Detailed Palworld status is not implemented yet."""


def message(server, msg):
    """Palworld has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Palworld server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Palworld datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("exe_name", "dir", "queryport"):
        return str(value[0])
    if key[0] == "publiclobby":
        return str(value[0]).lower() in ("1", "true", "yes", "on")
    raise ServerError("Unsupported key")
