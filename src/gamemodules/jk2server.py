"""Jedi Knight II: Jedi Outcast dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

JK2_DEDICATED_URL = (
    "https://mrwonko.de/jk3files/Jedi%20Outcast/Official%20Releases/Patches/2711/Jedi%20Knight%20II%20Linux%20Dedicated%20Server%201.03a.tar.gz"
)
JK2_DEDICATED_NAME = "jk2ded-1.03a.tar.gz"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Jedi Outcast in", str),
        ),
        options=(
            OptSpec("u", ["url"], "Download URL to use.", "url", "URL", str),
            OptSpec("n", ["download-name"], "Archive filename to cache.", "download_name", "NAME", str),
        ),
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _compression(server):
    """Infer the archive compression format from the configured download name."""

    name = server.data["download_name"].lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "tar.gz"
    if name.endswith(".tar"):
        return "tar"
    raise ServerError("Unable to determine archive type")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    download_name=None,
    exe_name="jk2mvded.x86_64",
):
    """Collect and store configuration values for a Jedi Outcast server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("fs_game", "base")
    server.data.setdefault("startmap", "ffa_bespin")
    server.data.setdefault("backupfiles", ["base"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["base"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 28070)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Jedi Outcast server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        server.data["url"] = JK2_DEDICATED_URL
    if ask and url is None:
        inp = input("Direct archive URL for the Jedi Outcast server override [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or JK2_DEDICATED_NAME
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Jedi Outcast server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = JK2_DEDICATED_URL
        server.data.setdefault("download_name", JK2_DEDICATED_NAME)
    install_archive(server, _compression(server))


def get_start_command(server):
    """Build the command used to launch a Jedi Outcast dedicated server."""

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
            "+map",
            server.data["startmap"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Jedi Outcast using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed Jedi Outcast status is not implemented yet."""


def message(server, msg):
    """Jedi Outcast has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Jedi Outcast server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Jedi Outcast datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "fs_game", "startmap", "hostname"):
        return str(value[0])
    raise ServerError("Unsupported key")
