"""Counter-Strike 2-specific lifecycle, configuration, and update helpers."""

import os
import re

from server import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.fileutils import make_empty_file
from utils.valve_server import (
    integration_source_server_config,
    source_query_address,
    wake_source_server_for_a2s,
)
import server.runtime as runtime_module
import utils.steamcmd as steamcmd

steam_app_id = 730
steam_anonymous_login_possible = True
wake_a2s_query = wake_source_server_for_a2s

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The Directory to install minecraft in", str),
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
                "Restarts the server upon updating",
                "restart",
                None,
                True,
            ),
        )
    ),
    "restart": CmdSpec(),
}
command_descriptions = {
    "update": "Updates the game server to the latest version.",
    "restart": "Restarts the game server without killing the process.",
}
command_functions = {}
max_stop_wait = 1

_confpat = re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s* (?:\s*(\S+))?(\s*)\Z")


def updateconfig(filename, settings):
    """Rewrite a simple key/value config file with the provided settings."""

    lines = []
    if os.path.isfile(filename):
        settings = settings.copy()
        with open(filename, "r", encoding="utf-8") as handle:
            for line in handle:
                match = _confpat.match(line)
                if match is not None and match.group(1) in settings:
                    lines.append(match.expand(r"\1 " + settings[match.group(1)] + r"\3"))
                    del settings[match.group(1)]
                else:
                    lines.append(line)
    for key, value in settings.items():
        lines.append(key + " " + value + "\n")
    with open(filename, "w", encoding="utf-8") as handle:
        handle.write("".join(lines))


def configure(server, ask, port=None, dir=None, *, exe_name="game/cs2.sh"):
    """Create the basic Counter-Strike 2 configuration details."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data["startmap"] = "de_dust2"
    server.data["maxplayers"] = "16"

    if port is None:
        port = server.data.get("port", 27015)
    if ask:
        while True:
            inp = input(
                "Please specify the port to use for this server: "
                + ("(current=" + str(port) + ") " if port is not None else "")
            ).strip()
            if port is not None and inp == "":
                break
            try:
                port = int(inp)
            except ValueError:
                print(inp + " isn't a valid port number")
                continue
            break
    if port is None:
        raise ValueError("No Port")
    server.data["port"] = port

    if dir is None:
        if "dir" in server.data and server.data["dir"] is not None:
            dir = server.data["dir"]
        else:
            dir = os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the cs2 server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = os.path.join(dir, "")

    if "exe_name" not in server.data:
        server.data["exe_name"] = exe_name
    server.data.save()
    return (), {}


def doinstall(server):
    """Install the Counter-Strike 2 server files via SteamCMD."""

    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])

    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=True,
    )


def install(server):
    """Install or prepare the Counter-Strike 2 server files."""

    doinstall(server)
    server_cfg = os.path.join(server.data["dir"], "game", "csgo", "cfg", "server.cfg")
    os.makedirs(os.path.dirname(server_cfg), exist_ok=True)
    if not os.path.isfile(server_cfg):
        make_empty_file(server_cfg)
    integration_cfg = integration_source_server_config()
    if integration_cfg:
        updateconfig(server_cfg, dict(integration_cfg))


def restart(server):
    """Restart the server by stopping it and then starting it again."""

    server.stop()
    server.start()


def update(server, validate=False, restart=False):
    """Update the CS2 install through SteamCMD and optionally restart it."""

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


def get_start_command(server):
    """Build the command list used to launch the Counter-Strike 2 server."""

    exe_name = server.data["exe_name"]
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if exe_name[:2] != "./":
        exe_name = "./" + exe_name

    return [
        exe_name,
        "-dedicated",
        "-console",
        "-usercon",
        "-port",
        str(server.data["port"]),
        "+map",
        str(server.data["startmap"]),
        "-maxplayers",
        str(server.data["maxplayers"]),
    ], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running CS2 server."""

    runtime_module.send_to_server(server, "\nquit\n")


def get_query_address(server):
    """Return the live CS2 query endpoint."""

    return source_query_address(server)


def get_info_address(server):
    """Return the live CS2 info endpoint."""

    return source_query_address(server)


def status(server, verbose):
    """Report CS2 server status information."""

    pass


command_functions = {
    "update": update,
    "restart": restart,
}


def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
    )


def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=get_start_command,
        port_definitions=(
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        stdin_open=True,
    )
