"""Quake 2 dedicated server lifecycle helpers."""

import os
import re
import subprocess as sp
import urllib.parse
import urllib.request

import downloader
import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.archive_install import resolve_archive_root, sync_tree
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.github_releases import HTTP_USER_AGENT, read_json

YAMAGI_Q2_PAGE = "https://www.yamagi.org/quake2/"
YAMAGI_Q2_TAGS_API = "https://api.github.com/repos/yquake2/yquake2/tags?per_page=100"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Quake 2 in", str),
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
    """Resolve the official Yamagi Quake II source archive."""

    if version not in (None, "", "latest"):
        tags = read_json(YAMAGI_Q2_TAGS_API)
        for tag in tags:
            tag_name = tag.get("name", "")
            if str(version) in tag_name:
                archive_url = (
                    "https://github.com/yquake2/yquake2/archive/refs/tags/%s.tar.gz"
                    % (urllib.parse.quote(tag_name, safe=""),)
                )
                return str(version), archive_url
        raise ServerError("Unable to locate the requested Yamagi Quake II version")
    request = urllib.request.Request(YAMAGI_Q2_PAGE, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        page = response.read().decode("utf-8")
    match = re.search(
        r'href="([^"]+)">Yamagi Quake II, Version ([0-9.]+)',
        page,
        re.IGNORECASE,
    )
    if match is None:
        raise ServerError("Unable to locate the latest Yamagi Quake II source archive")
    return match.group(2), urllib.parse.urljoin(YAMAGI_Q2_PAGE, match.group(1))


def _install_from_source(server):
    """Build q2ded from the resolved Yamagi Quake II source archive."""

    downloadpath = downloader.getpath(
        "url", (server.data["url"], server.data["download_name"], "tar.gz")
    )
    source_root = resolve_archive_root(downloadpath)
    if (
        server.data.get("current_url") != server.data["url"]
        or not os.path.isfile(os.path.join(server.data["dir"], server.data["exe_name"]))
    ):
        sp.run(["make"], cwd=source_root, check=True)
        sync_tree(source_root, server.data["dir"])
        server.data["current_url"] = server.data["url"]
        server.data.save()
    else:
        print("Skipping download")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="q2ded",
):
    """Collect and store configuration values for a Quake 2 server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("gamedir", "baseq2")
    server.data.setdefault("startmap", "q2dm1")
    server.data.setdefault("backupfiles", ["baseq2"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["baseq2"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27910)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Quake 2 server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
        server.data["download_mode"] = "archive"
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data["download_mode"] = "source-build"
    if ask and url is None:
        inp = input("Direct archive URL for the Quake 2 server override [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
            server.data["download_mode"] = "archive"
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "q2server.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Quake 2 server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
        server.data["download_mode"] = "source-build"
    if server.data.get("download_mode") == "source-build":
        _install_from_source(server)
        return
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Quake 2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "+set",
            "game",
            server.data["gamedir"],
            "+set",
            "hostname",
            server.data["hostname"],
            "+set",
            "port",
            str(server.data["port"]),
            "+map",
            server.data["startmap"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Quake 2 using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed Quake 2 status is not implemented yet."""


def message(server, msg):
    """Quake 2 has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake 2 server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Quake 2 datastore edits."""

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
        "gamedir",
        "startmap",
        "hostname",
        "version",
        "download_mode",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")
