"""GoldenEye: Source dedicated server lifecycle helpers."""

import os
import re
import urllib.request

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module

GES_SERVER_DOWNLOADS_PAGE = "https://www.geshl2.com/server-downloads/"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the GoldenEye: Source server", int),
            ArgSpec("DIR", "The directory to install GoldenEye: Source in", str),
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


def resolve_download():
    """Resolve the current GoldenEye: Source server archive redirect URL."""

    request = urllib.request.Request(
        GES_SERVER_DOWNLOADS_PAGE,
        headers={"User-Agent": "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"},
    )
    with urllib.request.urlopen(request) as response:
        page = response.read().decode("utf-8")
    name_match = re.search(r"Name:(?:</strong>)?\s*([A-Za-z0-9_.-]+)", page)
    url_match = re.search(r'href="([^"]*/go/[^"]*moddb/[^"]*)"', page)
    if name_match is None or url_match is None:
        raise ServerError("Unable to locate the current GoldenEye: Source server download")
    filename = name_match.group(1)
    version_match = re.search(r"_v([0-9.]+)_", filename)
    version = version_match.group(1) if version_match is not None else None
    download_url = url_match.group(1)
    if download_url.startswith("/"):
        download_url = "https://www.geshl2.com" + download_url
    return version, filename, download_url


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    download_name=None,
    exe_name="srcds_run",
):
    """Collect and store configuration values for a GoldenEye: Source server."""

    server.data.setdefault("game", "gesource")
    server.data.setdefault("maxplayers", "16")
    server.data.setdefault("startmap", "ge_archives")
    server.data.setdefault("backupfiles", ["gesource", "gesource/cfg"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["gesource", "gesource/cfg"]}},
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
            inp = input("Where would you like to install the GoldenEye: Source server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        resolved_version, resolved_name, resolved_url = resolve_download()
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", resolved_name)
    if ask and url is None:
        inp = input(
            "Direct archive URL for the GoldenEye: Source server: [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "goldeneye-source-server.zip"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the GoldenEye: Source server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_name, resolved_url = resolve_download()
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", resolved_name)
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a GoldenEye: Source dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-game",
            server.data["game"],
            "+map",
            server.data["startmap"],
            "+maxplayers",
            str(server.data["maxplayers"]),
            "-port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop GoldenEye: Source using the standard shell interrupt."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed GoldenEye: Source status is not implemented yet."""


def message(server, msg):
    """GoldenEye: Source has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a GoldenEye: Source server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported GoldenEye: Source datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "maxplayers"):
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "game", "startmap", "version"):
        return str(value[0])
    raise ServerError("Unsupported key")

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
