"""Core Keeper dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

steam_app_id = 1963720
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Core Keeper in", str),
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
    "update": "Update the Core Keeper dedicated server to the latest version.",
    "restart": "Restart the Core Keeper dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def _patch_launch_script(server):
    launch_path = os.path.join(server.data["dir"], "_launch.sh")
    if not os.path.isfile(launch_path):
        return
    original = open(launch_path, encoding="utf-8", errors="replace").read()
    old = (
        "    set -m\n\n"
        "    rm -f /tmp/.X99-lock\n\n"
        "    Xvfb :99 -screen 0 1x1x24 -nolisten tcp &\n"
        "    xvfbpid=$!\n\n"
        "    DISPLAY=:99 LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH:$installdir/linux64/\" \\\n"
        "\t   \"$exepath\" -batchmode -logfile CoreKeeperServerLog.txt \"$@\" &\n"
    )
    new = (
        "    xvfb-run -a --server-args=\"-screen 0 1x1x24 -nolisten tcp\" \\\n"
        "        env LD_LIBRARY_PATH=\"$LD_LIBRARY_PATH:$installdir/linux64/\" \\\n"
        "        \"$exepath\" -batchmode -logfile CoreKeeperServerLog.txt \"$@\" &\n"
    )
    if old not in original:
        return
    with open(launch_path, "w", encoding="utf-8") as handle:
        handle.write(original.replace(old, new))


def configure(server, ask, port=None, dir=None, *, exe_name="CoreKeeperServer"):
    """Collect and store configuration values for a Core Keeper server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("world", server.name)
    server.data.setdefault("worldindex", "0")
    server.data.setdefault("maxplayers", "8")
    server.data.setdefault("backupfiles", ["DedicatedServer", "GameInfo.txt", "GameID.txt"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["DedicatedServer", "GameInfo.txt", "GameID.txt"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27015)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Core Keeper server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", "_launch.sh")
    server.data.save()
    return (), {}


def install(server):
    """Download the Core Keeper server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )
    _patch_launch_script(server)


def update(server, validate=False, restart=False):
    """Update the Core Keeper server files and optionally restart the server."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(server.data["dir"], steam_app_id, steam_anonymous_login_possible, validate=validate)
    _patch_launch_script(server)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def restart(server):
    """Restart the Core Keeper server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Core Keeper dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-world",
            str(server.data["worldindex"]),
            "-worldname",
            server.data["world"],
            "-port",
            str(server.data["port"]),
            "-maxplayers",
            str(server.data["maxplayers"]),
            "-datapath",
            os.path.join(server.data["dir"], "DedicatedServer"),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the UDP endpoint used for Core Keeper reachability checks."""

    return ("127.0.0.1", int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the UDP endpoint used for Core Keeper info output."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Core Keeper by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Core Keeper status is not implemented yet."""


def message(server, msg):
    """Core Keeper has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Core Keeper server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Core Keeper datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "maxplayers", "worldindex"):
        return int(value[0])
    if key[0] in ("world", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")
