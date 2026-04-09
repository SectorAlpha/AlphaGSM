"""CS:GO-specific lifecycle, configuration, and update helpers."""

import os
import urllib.request
import json
import time
import datetime
import subprocess as sp
from server import ServerError
import re
import screen
import downloader
import utils.updatefs
from utils.cmdparse.cmdspec import CmdSpec, OptSpec, ArgSpec
from utils import backups
from utils import updatefs
import random

from utils.fileutils import make_empty_file
from utils.valve_server import integration_source_server_config, wake_source_server_for_a2s

import utils.steamcmd as steamcmd

import server.runtime as runtime_module

steam_app_id = 740
steam_anonymous_login_possible = True

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

# required still
command_descriptions = {
    "update": "Updates the game server to the latest version.",
    "restart": "Restarts the game server without killing the process.",
}


# required still
command_descriptions = {}
command_functions = {}  # will have elements added as the functions are defined

wake_a2s_query = wake_source_server_for_a2s

max_stop_wait = 1

_confpat = re.compile(r"\s*([^ \t\n\r\f\v#]\S*)\s* (?:\s*(\S+))?(\s*)\Z")


def updateconfig(filename, settings):
    """Rewrite a simple key/value config file with the provided settings."""
    lines = []
    if os.path.isfile(filename):
        settings = settings.copy()
        with open(filename, "r") as f:
            for l in f:
                m = _confpat.match(l)
                if m is not None and m.group(1) in settings:
                    lines.append(m.expand(r"\1 " + settings[m.group(1)] + r"\3"))
                    del settings[m.group(1)]
                else:
                    lines.append(l)
    for k, v in settings.items():
        lines.append(k + " " + v + "\n")
    print(lines)
    with open(filename, "w") as f:
        f.write("".join(lines))


def configure(server, ask, port=None, dir=None, *, exe_name="srcds_run"):
    """
    This function creates the configuration details for the server

    inputs:
        server: the server object
        ask: whether to request details (e.g port) from the user
        dir: the server installation dir
        *: All arguments after this are keyword only arguments
        exe_name: the executable name of the server
    """

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible

    # set some defaults
    server.data["mapgroup"] = "mg_active"
    server.data["startmap"] = "de_dust2"
    server.data["maxplayers"] = "16"
    server.data["gametype"] = "0"
    server.data["gamemode"] = "0"

    # do we have backup data already? if not initialise the dictionary
    if "backup" not in server.data:
        server.data["backup"] = {}
    if "profiles" not in server.data["backup"]:
        server.data["backup"]["profiles"] = {}
    # if no backup profile exists, create a basic one
    if len(server.data["backup"]["profiles"]) == 0:
        # essentially, the world, server properties and the root level json files are the best ones to back up. This can be configured though in the backup setup
        server.data["backup"]["profiles"]["default"] = {"targets": {}}
    if "schedule" not in server.data["backup"]:
        server.data["backup"]["schedule"] = []
    if len(server.data["backup"]["schedule"]) == 0:
        # if default does not exist, create it
        profile = "default"
        if profile not in server.data["backup"]["profiles"]:
            profile = next(iter(server.data["backup"]["profiles"]))
        # set the default to never back up
        server.data["backup"]["schedule"].append((profile, 0, "days"))

    # assign the port to the server
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
            except ValueError as v:
                print(inp + " isn't a valid port number")
                continue
            break
    if port is None:
        raise ValueError("No Port")
    server.data["port"] = port

    # assign install dir for the server
    if dir is None:
        if "dir" in server.data and server.data["dir"] is not None:
            dir = server.data["dir"]
        else:
            dir = os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the tf2 server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = os.path.join(
        dir, ""
    )  # guarentees the inclusion of trailing slashes.

    # if exe_name is not asigned, use the function default one
    if not "exe_name" in server.data:
        server.data["exe_name"] = (
            "srcds_run"  # don't use srcds_linux, as srcds_run sorts out your environment for you
        )
    server.data.save()

    return (), {}


def install(server):
    """Install or prepare the CS:GO server files for this server object."""
    doinstall(server)
    # TODO: any config files that need creating or any commands that need running before the server can start for the first time

    # create config file
    server_cfg = server.data["dir"] + "csgo/cfg/" + "server.cfg"
    cfg_exists = os.path.isfile(server_cfg)
    if cfg_exists == False:
        make_empty_file(server_cfg)
    integration_cfg = integration_source_server_config()
    if integration_cfg:
        updateconfig(server_cfg, integration_cfg)


# technically this command is not needed, but leaving it commented as an example
#  updateconfig(server_cfg,{"hostport":str(server.data["port"])})


def doinstall(server):
    """Do the installation of the latest version. Will be called by both the install function thats part of the setup command and by the auto updater"""
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])

    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=True,
    )


def restart(server):
    """Restart the server by stopping it and then starting it again."""
    server.stop()
    server.start()


def update(server, validate=False, restart=False):
    """Update the CS:GO install through SteamCMD and optionally restart it."""
    try:
        server.stop()
    except:
        print("Server has probably already stopped, updating")
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        validate=validate,
    )
    print("Server up to date")
    if restart == True:
        print("Starting the server up")
        server.start()


def _disable_incompatible_bundled_libgcc(server):
    """Move the bundled libgcc aside so Source uses the host runtime copy."""

    libgcc_path = os.path.join(server.data["dir"], "bin", "libgcc_s.so.1")
    disabled_path = libgcc_path + ".alphagsm-disabled"
    if os.path.isfile(libgcc_path):
        try:
            os.replace(libgcc_path, disabled_path)
        except FileNotFoundError:
            return disabled_path
        print(
            "Disabled bundled libgcc_s.so.1 for CS:GO/CS2 compatibility: "
            + disabled_path
        )
    return disabled_path


def get_start_command(server):
    """Build the command list used to launch the CS:GO dedicated server."""
    # sample start command
    # ./srcds_run -game csgo -console -usercon +game_type 0 +game_mode 0 +mapgroup mg_active +map de_dust2 -maxplayers 30
    exe_name = server.data["exe_name"]
    if not os.path.isfile(server.data["dir"] + exe_name):
        ServerError("Executable file not found")

    if exe_name[:2] != "./":
        exe_name = "./" + exe_name

    _disable_incompatible_bundled_libgcc(server)

    steamcmd_dir = steamcmd.STEAMCMD_DIR
    steam_updatescript = steamcmd.get_autoupdate_script(
        server.name, server.data["dir"], steam_app_id
    )

    return [
        exe_name,
        "-game",
        "csgo",
        "-console",
        "-usercon",
        "+game_type",
        str(server.data["gametype"]),
        "+game_mode",
        str(server.data["gamemode"]),
        "+sv_pure",
        "1",
        "+ip",
        "0.0.0.0",
        "-secured",
        "-timeout 0",
        "-strictportbind",
        "-port",
        str(server.data["port"]),
        "+mapgroup",
        str(server.data["mapgroup"]),
        "+map",
        str(server.data["startmap"]),
        "-maxplayers",
        str(server.data["maxplayers"]),
        "-autoupdate",
        "-steam_dir",
        steamcmd_dir,
        "-steamcmd_script",
        steam_updatescript,
        "+sv_shutdown_timeout_minutes",
        "2",
    ], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running CS:GO server."""
    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Report CS:GO server status information."""
    pass


# required, must be defined to allow functions listed below which are not in the defaults to be used
command_functions = {
    "update": update,
    "restart": restart,
}  # will have elements added as the functions are defined

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
    )
