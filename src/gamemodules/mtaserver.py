"""Multi Theft Auto dedicated server lifecycle helpers."""

import os
import re
import urllib.request

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

MTA_DOWNLOADS_PAGE = "https://linux.multitheftauto.com/"
MTA_LATEST_DOWNLOAD_NAME = "multitheftauto_linux_x64.tar.gz"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Multi Theft Auto in", str),
        ),
        options=(
            OptSpec("v", ["version"], "Version to download.", "version", "VERSION", str),
            OptSpec("u", ["url"], "Download URL to use.", "url", "URL", str),
            OptSpec("N", ["download-name"], "Archive filename to cache.", "download_name", "NAME", str),
        ),
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def resolve_download(version=None):
    """Resolve a Multi Theft Auto x86_64 Linux server package."""

    req = urllib.request.Request(MTA_DOWNLOADS_PAGE, headers={"User-Agent": "AlphaGSM"})
    with urllib.request.urlopen(req) as response:
        page = response.read().decode("utf-8")
    ver_match = re.search(r"Version\s+([0-9]+(?:\.[0-9]+)+)", page)
    if not ver_match:
        raise ServerError("Unable to locate Multi Theft Auto Linux server downloads")
    resolved_version = ver_match.group(1)
    url_match = re.search(r'href="([^"]*multitheftauto_linux_x64\.tar\.gz)"', page)
    if not url_match:
        raise ServerError("Unable to locate Multi Theft Auto Linux server downloads")
    resolved_url = url_match.group(1)
    if not resolved_url.startswith("http"):
        resolved_url = MTA_DOWNLOADS_PAGE.rstrip("/") + "/" + resolved_url.lstrip("/")
    if version not in (None, "", "latest") and version != resolved_version:
        raise ServerError("Unable to locate the requested Multi Theft Auto version")
    return resolved_version, resolved_url


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="mta-server64"
):
    """Collect and store configuration values for a Multi Theft Auto server."""

    server.data.setdefault("backupfiles", ["mods", "server", "mods/deathmatch/mtaserver.conf"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["mods", "server"]}},
            "schedule": [("default", 0, "days")],
        }
    if port is None:
        port = server.data.get("port", 22003)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Multi Theft Auto server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input(
            "Direct archive URL for the Multi Theft Auto server: [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = (
            os.path.basename(server.data.get("url", "")) or MTA_LATEST_DOWNLOAD_NAME
        )
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Multi Theft Auto server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url) or MTA_LATEST_DOWNLOAD_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Multi Theft Auto dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "--port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop MTA using the standard shutdown command."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed Multi Theft Auto status is not implemented yet."""


def message(server, msg):
    """Multi Theft Auto has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Multi Theft Auto server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Multi Theft Auto datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "version"):
        return str(value[0])
    raise ServerError("Unsupported key")
