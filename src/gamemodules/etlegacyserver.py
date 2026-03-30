"""ET: Legacy dedicated server lifecycle helpers."""

import os
import re
import urllib.request

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

ETLEGACY_DOWNLOAD_PAGE = "https://www.etlegacy.com/download"
ETLEGACY_RELEASE_LIST_PAGE = "https://www.etlegacy.com/download/release/list"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install ET: Legacy in", str),
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


def _read_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": "AlphaGSM/1.0"})
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8", "replace")


def _parse_release_page(page_html):
    version_match = re.search(r"stable release ([0-9.]+)", page_html, re.IGNORECASE)
    download_match = re.search(
        r"Linux.*?data-href=\"(https://www\.etlegacy\.com/download/file/\d+)\">x86_64 archive",
        page_html,
        re.IGNORECASE | re.DOTALL,
    )
    if version_match is None or download_match is None:
        raise ServerError("Unable to locate a suitable ET: Legacy Linux download")
    version = version_match.group(1)
    return version, download_match.group(1)


def resolve_download(version=None):
    """Resolve an ET: Legacy Linux server archive from the official downloads site."""

    if version in (None, "", "latest"):
        return _parse_release_page(_read_page(ETLEGACY_DOWNLOAD_PAGE))

    release_list = _read_page(ETLEGACY_RELEASE_LIST_PAGE)
    release_match = re.search(
        r'href="https://www\.etlegacy\.com/download/release/(\d+)">%s\b'
        % re.escape(str(version)),
        release_list,
        re.IGNORECASE,
    )
    if release_match is None:
        raise ServerError("Unable to locate the requested ET: Legacy release")
    release_url = "https://www.etlegacy.com/download/release/%s" % (release_match.group(1),)
    resolved_version, resolved_url = _parse_release_page(_read_page(release_url))
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
    exe_name="etl.x86_64",
):
    """Collect and store configuration values for an ET: Legacy server."""

    server.data.setdefault("fs_game", "legacy")
    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("configfile", "etl_server.cfg")
    server.data.setdefault("backupfiles", ["legacy", "etmain"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["legacy", "etmain"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27960)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the ET: Legacy server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        requested_version = version or server.data.get("version")
        resolved_version, resolved_url = resolve_download(version=requested_version)
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if ask and url is None:
        inp = input(
            "Direct archive URL for the ET: Legacy server: [%s] " % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        if server.data.get("version"):
            server.data["download_name"] = "etlegacy-v%s-x86_64.tar.gz" % (server.data["version"],)
        else:
            server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "etlegacy.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the ET: Legacy server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", "etlegacy-v%s-x86_64.tar.gz" % (resolved_version,))
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch an ET: Legacy dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "+set",
            "fs_game",
            server.data["fs_game"],
            "+set",
            "net_port",
            str(server.data["port"]),
            "+set",
            "sv_hostname",
            server.data["hostname"],
            "+exec",
            server.data["configfile"],
            "+set",
            "dedicated",
            "2",
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """ET: Legacy uses the Quake3/ioquake3 getstatus query on the game port."""
    return ("127.0.0.1", int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake3 address used by the info command."""
    return ("127.0.0.1", int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop ET: Legacy using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed ET: Legacy status is not implemented yet."""


def message(server, msg):
    """ET: Legacy has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for an ET: Legacy server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported ET: Legacy datastore edits."""

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
        "fs_game",
        "configfile",
        "hostname",
        "version",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")
