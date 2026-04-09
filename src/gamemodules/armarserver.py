"""Arma Reforger dedicated server lifecycle helpers."""

import json
import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

steam_app_id = 1874900
steam_anonymous_login_possible = True
DEFAULT_SCENARIO_ID = "{ECC61978EDCC2B5A}Missions/23_Campaign.conf"

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Arma Reforger in", str),
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
    "update": "Update the Arma Reforger dedicated server to the latest version.",
    "restart": "Restart the Arma Reforger dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="ArmaReforgerServer"):
    """Collect and store configuration values for an Arma Reforger server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("configfile", "configs/server.json")
    server.data.setdefault("profilesdir", "profile")
    server.data.setdefault("bindaddress", "0.0.0.0")
    server.data.setdefault("scenarioid", DEFAULT_SCENARIO_ID)
    server.data.setdefault("maxplayers", 8)
    server.data.setdefault("backupfiles", ["configs", "profile"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["configs", "profile"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 2001)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    server.data.setdefault("queryport", int(server.data["port"]) + 1)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Arma Reforger server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Arma Reforger server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )
    config_dir = os.path.join(server.data["dir"], os.path.dirname(server.data["configfile"]))
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    os.makedirs(os.path.join(server.data["dir"], server.data["profilesdir"]), exist_ok=True)

    config_path = os.path.join(server.data["dir"], server.data["configfile"])
    if not os.path.isfile(config_path):
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "a2s": {
                        "address": server.data.get("bindaddress", "0.0.0.0"),
                        "port": int(server.data.get("queryport", int(server.data.get("port", 2001)) + 1)),
                    },
                    "game": {
                        "name": server.name,
                        "admins": [],
                        "passwordAdmin": "",
                        "maxPlayers": int(server.data.get("maxplayers", 8)),
                        "crossPlatform": False,
                        "supportedPlatforms": ["PLATFORM_PC"],
                        "scenarioId": server.data.get(
                            "scenarioid", DEFAULT_SCENARIO_ID
                        ),
                    }
                },
                handle,
                indent=2,
            )
            handle.write("\n")
    server.data.save()


def update(server, validate=False, restart=False):
    """Update the Arma Reforger server files and optionally restart the server."""

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
    """Restart the Arma Reforger server."""

    server.stop()
    server.start()


def _build_start_command(server):
    """Build the Arma Reforger start command without install-state checks."""

    config_path = os.path.join(server.data["dir"], server.data["configfile"])
    profile_path = os.path.join(server.data["dir"], server.data["profilesdir"])
    return (
        [
            "./" + server.data["exe_name"],
            "-config",
            config_path,
            "-profile",
            profile_path,
            "-bindAddress",
            server.data["bindaddress"],
            "-bindPort",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def get_start_command(server):
    """Build the command used to launch an Arma Reforger dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    config_path = os.path.join(server.data["dir"], server.data["configfile"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if not os.path.isfile(config_path):
        raise ServerError("Config file not found")
    return _build_start_command(server)


def get_runtime_requirements(server):
    """Return Docker runtime metadata for Arma Reforger."""

    requirements = {
        "engine": "docker",
        "family": "steamcmd-linux",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    ports = []
    for key in ("port", "queryport"):
        if key in server.data and server.data[key] is not None:
            ports.append(
                {
                    "host": int(server.data[key]),
                    "container": int(server.data[key]),
                    "protocol": "udp",
                }
            )
    if ports:
        requirements["ports"] = ports
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Arma Reforger."""

    cmd, _cwd = _build_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Return the A2S query address used by Arma Reforger."""

    return ("127.0.0.1", int(server.data.get("queryport", int(server.data["port"]) + 1)), "a2s")


def get_info_address(server):
    """Return the A2S info address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Arma Reforger by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Arma Reforger status is not implemented yet."""


def message(server, msg):
    """Arma Reforger has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an Arma Reforger server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Arma Reforger datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] == "queryport":
        return int(value[0])
    if key[0] == "maxplayers":
        return int(value[0])
    if key[0] == "scenarioid":
        return str(value[0])
    if key[0] in ("configfile", "profilesdir", "bindaddress", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")
