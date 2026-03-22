"""Trackmania dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

TRACKMANIA_SERVER_URL = "http://files2.trackmaniaforever.com/TrackmaniaServer_2011-02-21.zip"
TRACKMANIA_SERVER_NAME = "TrackmaniaServer_2011-02-21.zip"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The XML-RPC port to use for the Trackmania server", int),
            ArgSpec("DIR", "The directory to install Trackmania in", str),
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
    exe_name="TrackmaniaServer",
):
    """Collect and store configuration values for a Trackmania server."""

    server.data.setdefault("dedicated_cfg", "dedicated_cfg.txt")
    server.data.setdefault("game_settings", "MatchSettings/Nations/NationsGreen.txt")
    server.data.setdefault("backupfiles", ["GameData/Config", "UserData", "Logs"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["GameData/Config", "UserData", "Logs"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 5000)
    if ask:
        inp = input("Please specify the XML-RPC port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install Trackmania in: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data:
        server.data["url"] = TRACKMANIA_SERVER_URL
    if ask and url is None:
        inp = input(
            "Direct archive URL for the Trackmania dedicated server override [%s] "
            % (server.data["url"],)
        ).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = (
            os.path.basename(server.data.get("url", "")) or TRACKMANIA_SERVER_NAME
        )
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Trackmania server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = TRACKMANIA_SERVER_URL
        server.data.setdefault("download_name", TRACKMANIA_SERVER_NAME)
    install_archive(server, _compression(server))


def get_start_command(server):
    """Build the command used to launch a Trackmania dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "/dedicated_cfg=%s" % (server.data["dedicated_cfg"],),
            "/game_settings=%s" % (server.data["game_settings"],),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Trackmania by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Trackmania status is not implemented yet."""


def message(server, msg):
    """Trackmania has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Trackmania server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Trackmania datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "dedicated_cfg", "game_settings"):
        return str(value[0])
    raise ServerError("Unsupported key")
