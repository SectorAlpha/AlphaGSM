"""Call of Duty dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

COD_SERVER_URL = "https://0day.icculus.org/cod/COD-lnxded-1.5-large.tar.bz2"
COD_SERVER_NAME = "COD-lnxded-1.5-large.tar.bz2"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Call of Duty in", str),
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
    name = server.data["download_name"].lower()
    if name.endswith(".zip"):
        return "zip"
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "tar.gz"
    if name.endswith(".tar"):
        return "tar"
    raise ServerError("Unable to determine archive type")


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="cod_lnxded"):
    """Collect and store configuration values for a Call of Duty server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("moddir", "main")
    server.data.setdefault("startmap", "mp_carentan")
    server.data.setdefault("backupfiles", ["main"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["main"]}},
            "schedule": [("default", 0, "days")],
        }
    if port is None:
        port = server.data.get("port", 28960)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Call of Duty server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        server.data["url"] = COD_SERVER_URL
    if ask and url is None:
        inp = input("Direct archive URL for the Call of Duty server override [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or COD_SERVER_NAME
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Call of Duty server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = COD_SERVER_URL
        server.data.setdefault("download_name", COD_SERVER_NAME)
    install_archive(server, _compression(server))


def get_start_command(server):
    """Build the command used to launch a Call of Duty dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "+set",
            "fs_game",
            server.data["moddir"],
            "+set",
            "sv_hostname",
            server.data["hostname"],
            "+set",
            "net_port",
            str(server.data["port"]),
            "+map",
            server.data["startmap"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Call of Duty using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed Call of Duty status is not implemented yet."""


def message(server, msg):
    """Call of Duty has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Call of Duty server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Call of Duty datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "moddir", "startmap", "hostname"):
        return str(value[0])
    raise ServerError("Unsupported key")
