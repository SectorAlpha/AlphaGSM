"""Xonotic dedicated server lifecycle helpers."""

import os
import re
import urllib.request

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

XONOTIC_DOWNLOAD_PAGE = "https://xonotic.org/download/"
XONOTIC_DOWNLOAD_TEMPLATE = "https://dl.xonotic.org/xonotic-%s.zip"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Xonotic in", str),
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
    """Resolve an official Xonotic release zip URL."""

    if version not in (None, "", "latest"):
        return version, XONOTIC_DOWNLOAD_TEMPLATE % (version,)
    with urllib.request.urlopen(XONOTIC_DOWNLOAD_PAGE) as response:
        page = response.read().decode("utf-8")
    match = re.search(r"Download Xonotic ([0-9]+(?:\.[0-9]+)+)", page)
    if match is None:
        raise ServerError("Unable to locate the latest Xonotic release version")
    version = match.group(1)
    return version, XONOTIC_DOWNLOAD_TEMPLATE % (version,)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="xonotic-linux64-dedicated",
):
    """Collect and store configuration values for a Xonotic server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("gametype", "dm")
    server.data.setdefault("userdir", "server")
    server.data.setdefault("backupfiles", ["server", "data"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["server", "data"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 26000)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Xonotic server: [%s] " % (dir,)).strip()
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
        inp = input("Direct archive URL for the Xonotic server: [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "xonotic-server.zip"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Xonotic server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Xonotic dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-userdir",
            os.path.join(server.data["dir"], server.data["userdir"]),
            "+sv_public",
            "1",
            "+port",
            str(server.data["port"]),
            "+g_gametype",
            server.data["gametype"],
            "+hostname",
            server.data["hostname"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Xonotic using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed Xonotic status is not implemented yet."""


def message(server, msg):
    """Xonotic has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Xonotic server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Xonotic datastore edits."""

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
        "userdir",
        "gametype",
        "hostname",
        "version",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")
