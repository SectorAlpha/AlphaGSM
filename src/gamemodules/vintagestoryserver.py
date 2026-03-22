"""Vintage Story dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

VINTAGE_STORY_DOWNLOAD_TEMPLATE = (
    "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_%s.tar.gz"
)

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Vintage Story server", int),
            ArgSpec("DIR", "The directory to install Vintage Story in", str),
        ),
        options=(
            OptSpec("v", ["version"], "Version to download.", "version", "VERSION", str),
            OptSpec("u", ["url"], "Download URL to use.", "url", "URL", str),
            OptSpec("n", ["download-name"], "Archive filename to cache.", "download_name", "NAME", str),
        ),
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def resolve_download(version):
    """Construct the documented Vintage Story server tarball URL for a version."""

    if version in (None, "", "latest"):
        raise ServerError("A specific Vintage Story version is required unless a direct URL is supplied")
    return version, VINTAGE_STORY_DOWNLOAD_TEMPLATE % (version,)


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
    version=None,
    url=None,
    download_name=None,
    exe_name="VintagestoryServer",
):
    """Collect and store configuration values for a Vintage Story server."""

    server.data.setdefault("worldname", server.name)
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("backupfiles", ["Data", "Saves", "serverconfig.json"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Data", "Saves", "serverconfig.json"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 42420)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Vintage Story server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
    elif version is not None or server.data.get("version") not in (None, ""):
        resolved_version, resolved_url = resolve_download(version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    elif "url" not in server.data and ask:
        inp = input("Direct archive URL for the Vintage Story server: ").strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "vintagestory-server.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Vintage Story server archive."""

    if "url" not in server.data or not server.data["url"]:
        if server.data.get("version") not in (None, ""):
            resolved_version, resolved_url = resolve_download(server.data["version"])
            server.data["version"] = resolved_version
            server.data["url"] = resolved_url
            server.data.setdefault("download_name", os.path.basename(resolved_url))
        else:
            raise ServerError("A direct download URL or version is required for this server")
    install_archive(server, _compression(server))


def get_start_command(server):
    """Build the command used to launch a Vintage Story dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "--dataPath",
            server.data["dir"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Vintage Story using the standard shutdown command."""

    screen.send_to_server(server.name, "\nstop\n")


def status(server, verbose):
    """Detailed Vintage Story status is not implemented yet."""


def message(server, msg):
    """Vintage Story has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Vintage Story server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Vintage Story datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("url", "download_name", "exe_name", "dir", "worldname", "servername", "version"):
        return str(value[0])
    raise ServerError("Unsupported key")
