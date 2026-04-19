"""Unreal Tournament 2004 dedicated server lifecycle helpers."""

import os
import stat
import subprocess as sp

import downloader
import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

UT2K4_INSTALLER_URL = (
    "https://raw.githubusercontent.com/OldUnreal/FullGameInstallers/master/Linux/install-ut2004.sh"
)
UT2K4_INSTALLER_NAME = "install-ut2004.sh"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Unreal Tournament 2004 in", str),
        ),
        options=(
            OptSpec("u", ["url"], "Download URL to use.", "url", "URL", str),
            OptSpec("N", ["download-name"], "Archive filename to cache.", "download_name", "NAME", str),
        ),
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    download_name=None,
    exe_name="System/ucc-bin",
):
    """Collect and store configuration values for an Unreal Tournament 2004 server."""

    server.data.setdefault("startmap", "DM-Antalus")
    server.data.setdefault("gametype", "XGame.xDeathMatch")
    server.data.setdefault("maxplayers", "16")
    server.data.setdefault("configfile", "System/UT2004.ini")
    server.data.setdefault("backupfiles", ["System", "Maps"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["System", "Maps"]}},
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
            inp = input(
                "Where would you like to install the Unreal Tournament 2004 server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        server.data["url"] = UT2K4_INSTALLER_URL
        server.data["download_mode"] = "installer"
    if ask and url is None:
        inp = input(
            "Direct archive URL for the Unreal Tournament 2004 server override [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
            server.data["download_mode"] = "archive"
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or UT2K4_INSTALLER_NAME
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Install Unreal Tournament 2004 using the OldUnreal Linux installer."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = UT2K4_INSTALLER_URL
        server.data.setdefault("download_name", UT2K4_INSTALLER_NAME)
        server.data["download_mode"] = "installer"
    if server.data.get("download_mode") == "installer":
        download_path = downloader.getpath("url", (server.data["url"], server.data["download_name"]))
        installer_path = os.path.join(download_path, server.data["download_name"])
        mode = os.stat(installer_path).st_mode
        os.chmod(installer_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        if (
            server.data.get("current_url") != server.data["url"]
            or not os.path.isfile(os.path.join(server.data["dir"], server.data["exe_name"]))
        ):
            sp.run(
                [
                    installer_path,
                    "--destination",
                    server.data["dir"],
                    "--ui-mode",
                    "none",
                    "--application-entry",
                    "skip",
                    "--desktop-shortcut",
                    "skip",
                ],
                check=True,
            )
            server.data["current_url"] = server.data["url"]
            server.data.save()
        else:
            print("Skipping download")
        return
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch an Unreal Tournament 2004 server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "server",
            "%s?Game=%s?MaxPlayers=%s" % (
                server.data["startmap"],
                server.data["gametype"],
                server.data["maxplayers"],
            ),
            "-port=%s" % (server.data["port"],),
            "-ini=%s" % (server.data["configfile"],),
            "-log=server.log",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Unreal Tournament 2004 using the standard console command."""

    screen.send_to_server(server.name, "\nexit\n")


def status(server, verbose):
    """Detailed Unreal Tournament 2004 status is not implemented yet."""


def message(server, msg):
    """Unreal Tournament 2004 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Unreal Tournament 2004 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Unreal Tournament 2004 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=(
            "url",
            "download_name",
            "exe_name",
            "dir",
            "startmap",
            "gametype",
            "maxplayers",
            "configfile",
            "download_mode",
        ),
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
