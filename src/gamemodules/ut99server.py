"""Unreal Tournament 99 dedicated server lifecycle helpers."""

import os
import shutil
import stat
import subprocess as sp

import downloader
import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

UT99_INSTALLER_URL = (
    "https://raw.githubusercontent.com/OldUnreal/FullGameInstallers/master/Linux/install-ut99.sh"
)
UT99_INSTALLER_NAME = "install-ut99.sh"
UT99_LAYOUT_CANDIDATES = (
    ("System64/ucc-bin-amd64", "System64/UnrealTournament.ini"),
    ("System64/ucc-bin", "System64/UnrealTournament.ini"),
    ("SystemARM64/ucc-bin-arm64", "SystemARM64/UnrealTournament.ini"),
    ("SystemARM64/ucc-bin", "SystemARM64/UnrealTournament.ini"),
    ("System64/ut-bin-amd64", "System64/UnrealTournament.ini"),
    ("SystemARM64/ut-bin-arm64", "SystemARM64/UnrealTournament.ini"),
    ("System/ucc-bin", "System/UnrealTournament.ini"),
)


def _require_ut99_installer_prerequisites():
    """Raise when the OldUnreal installer prerequisites are not present."""

    if shutil.which("7zz") or shutil.which("7z"):
        return
    raise ServerError(
        "UT99 installer requires a 7z-compatible extractor. "
        "Install p7zip-full or another package that provides 7z/7zz."
    )


def _sync_installed_layout(server):
    """Update stored executable/config paths to match the installed UT99 layout."""

    dir_path = server.data["dir"]
    configfile = server.data.get("configfile")
    managed_config_paths = {ini_path for _exe_path, ini_path in UT99_LAYOUT_CANDIDATES}

    for exe_name, config_path in UT99_LAYOUT_CANDIDATES:
        if not os.path.isfile(os.path.join(dir_path, exe_name)):
            continue
        server.data["exe_name"] = exe_name
        if not configfile or configfile in managed_config_paths:
            server.data["configfile"] = config_path
        return

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Unreal Tournament 99 in", str),
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
    """Collect and store configuration values for an Unreal Tournament 99 server."""

    server.data.setdefault("startmap", "DM-Deck16][")
    server.data.setdefault("gametype", "Botpack.DeathMatchPlus")
    server.data.setdefault("maxplayers", "16")
    server.data.setdefault("configfile", "System/UnrealTournament.ini")
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
                "Where would you like to install the Unreal Tournament 99 server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        server.data["url"] = UT99_INSTALLER_URL
        server.data["download_mode"] = "installer"
    if ask and url is None:
        inp = input(
            "Direct archive URL for the Unreal Tournament 99 server override [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
            server.data["download_mode"] = "archive"
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or UT99_INSTALLER_NAME
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Install Unreal Tournament 99 using the OldUnreal Linux installer."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = UT99_INSTALLER_URL
        server.data.setdefault("download_name", UT99_INSTALLER_NAME)
        server.data["download_mode"] = "installer"
    if server.data.get("download_mode") == "installer":
        _require_ut99_installer_prerequisites()
        download_path = downloader.getpath("url", (server.data["url"], server.data["download_name"]))
        installer_path = os.path.join(download_path, server.data["download_name"])
        mode = os.stat(installer_path).st_mode
        os.chmod(installer_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        _sync_installed_layout(server)
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
                input="y\n",
                text=True,
                check=True,
            )
            _sync_installed_layout(server)
            server.data["current_url"] = server.data["url"]
            server.data.save()
        else:
            print("Skipping download")
        return
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch an Unreal Tournament 99 server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return _runtime_command(server)


def _runtime_command(server):
    """Return the UT99 runtime command without install-time existence checks."""

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
    """Stop Unreal Tournament 99 using the standard console command."""

    screen.send_to_server(server.name, "\nexit\n")


def get_query_address(server):
    """Probe the UT99 game socket as generic UDP reachability."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Use UDP reachability for UT99 info until a richer protocol is implemented."""

    return get_query_address(server)


def status(server, verbose):
    """Detailed Unreal Tournament 99 status is not implemented yet."""


def message(server, msg):
    """Unreal Tournament 99 has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an Unreal Tournament 99 server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Unreal Tournament 99 datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in (
        "url",
        "download_name",
        "exe_name",
        "dir",
        "startmap",
        "gametype",
        "maxplayers",
        "configfile",
        "download_mode",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )

def get_container_spec(server):
    command, _cwd = _runtime_command(server)
    requirements = runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    )
    return {
        "working_dir": runtime_module.DEFAULT_CONTAINER_WORKDIR,
        "stdin_open": True,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": list(command),
    }
