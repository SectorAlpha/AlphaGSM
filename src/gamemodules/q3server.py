"""Quake 3 Arena dedicated server lifecycle helpers."""

import os

import screen
import server.runtime as runtime_module
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.github_releases import resolve_release_asset

IOQ3_LATEST_RELEASE_API = "https://api.github.com/repos/ioquake/ioq3/releases/latest"

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to install Quake 3 in", str),
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
    """Resolve an ioquake3 Linux release asset suitable for a dedicated server."""

    def _matches(asset):
        name = asset.get("name", "").lower()
        return "linux" in name and "x86_64" in name and name.endswith(".zip")

    return resolve_release_asset(IOQ3_LATEST_RELEASE_API, _matches, version=version)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="q3ded.x86_64",
):
    """Collect and store configuration values for a Quake 3 server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("fs_game", "baseq3")
    server.data.setdefault("startmap", "q3dm17")
    server.data.setdefault("backupfiles", ["baseq3"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["baseq3"]}},
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
            inp = input("Where would you like to install the Quake 3 server: [%s] " % (dir,)).strip()
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
        inp = input("Direct archive URL for the Quake 3 server: [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "q3server.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Quake 3 server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Quake 3 dedicated server."""

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


def get_runtime_requirements(server):
    """Return Docker runtime metadata for native Linux Quake-family servers."""

    requirements = {
        "engine": "docker",
        "family": "quake-linux",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Quake 3."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Return the Quake UDP query address used by the q3server module."""

    return ("127.0.0.1", int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the q3server module."""

    return ("127.0.0.1", int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Quake 3 using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Quake 3 status is not implemented yet."""


def message(server, msg):
    """Quake 3 has no simple generic message console support here."""

    print("This server doesn't support generic messages yet")


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake 3 server."""

    backup_utils.backup(server.data["dir"], server.data["backup"], profile)


def checkvalue(server, key, *value):
    """Validate supported Quake 3 datastore edits."""

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
        "startmap",
        "hostname",
        "version",
    ):
        return str(value[0])
    raise ServerError("Unsupported key")
