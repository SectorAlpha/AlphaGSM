"""Bungeecord-specific setup and runtime helpers."""

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

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The Directory to install minecraft in", str),
        )
    )
}
command_descriptions = {}
command_functions = {}


def configure(server, ask, port=None, dir=None, *, exe_name="BungeeCord.jar"):
    """Collect and store configuration values for a Bungeecord server."""
    if dir is None:
        if "dir" in server.data and server.data["dir"] is not None:
            dir = server.data["dir"]
        else:
            dir = os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the minecraft server: [" + dir + "] "
            ).strip()
            if inp != "":
                dir = inp
    server.data["dir"] = dir

    if not "exe_name" in server.data:
        server.data["exe_name"] = exe_name
    server.data.save()

    return (), {}


def install(server, *, eula=False):
    """Install or validate the Bungeecord server files for this server."""
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    mcjar = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(mcjar):
        raise ServerError(
            "Can't find server jar ({}). Please place the files in the directory and/or update the 'exe_name' then run setup again".format(
                mcjar
            )
        )
    server.data.save()


def get_start_command(server):
    """Build the command list used to launch the Bungeecord server."""
    return ["java", "-Xmx256M", "-jar", server.data["exe_name"]], server.data["dir"]


def do_stop(server, j):
    """Send the console command used to stop a running Bungeecord server."""
    screen.send_to_server(server.name, "\nend\n")


def status(server, verbose):
    """Report Bungeecord server status information."""
    pass


def message(server, msg):
    """Explain that Bungeecord has no direct user-message support here."""
    print("This server doesn't have users directly")


def checkvalue(server, key, value):
    """Validate a proposed stored setting value for this server type."""
    if key == "exe_name":
        return value
    raise ServerError("All read only as not yet implemented")


def backup(server):
    """Explain that this server type has no dedicated backup implementation here."""
    print("This server doesn't have anything to backup")
