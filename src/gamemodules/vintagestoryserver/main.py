"""Vintage Story dedicated server lifecycle helpers."""

import json
import os
import re
import urllib.request

from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

VINTAGE_STORY_DOWNLOAD_TEMPLATE = (
    "https://cdn.vintagestory.at/gamefiles/stable/vs_server_linux-x64_%s.tar.gz"
)
VINTAGE_STORY_STABLE_API = "https://api.vintagestory.at/stable.json"
VINTAGE_STORY_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The game port to use for the Vintage Story server",
    "The directory to install Vintage Story in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _read_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": VINTAGE_STORY_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def _version_sort_key(version):
    return tuple(
        (0, int(token)) if token.isdigit() else (1, token)
        for token in re.split(r"([0-9]+)", version)
        if token
    )


def resolve_download(version):
    """Construct the documented Vintage Story server tarball URL for a version."""

    if version in (None, "", "latest"):
        stable_data = _read_json(VINTAGE_STORY_STABLE_API)
        if not isinstance(stable_data, dict):
            raise ServerError("Unable to locate Vintage Story stable release metadata")

        for candidate_version, metadata in stable_data.items():
            linux_server = metadata.get("linuxserver") or {}
            cdn_url = (linux_server.get("urls") or {}).get("cdn")
            if linux_server.get("latest") == 1 and cdn_url:
                return candidate_version, cdn_url

        for candidate_version in sorted(stable_data, key=_version_sort_key, reverse=True):
            linux_server = (stable_data.get(candidate_version) or {}).get("linuxserver") or {}
            cdn_url = (linux_server.get("urls") or {}).get("cdn")
            if cdn_url:
                return candidate_version, cdn_url

        raise ServerError("Unable to locate a stable Vintage Story Linux server download")
    return version, VINTAGE_STORY_DOWNLOAD_TEMPLATE % (version,)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="VintagestoryServer.dll",
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
    else:
        resolved_version, resolved_url = resolve_download(version or server.data.get("version") or "latest")
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
    if "url" not in server.data and ask:
        inp = input("Direct archive URL for the Vintage Story server: ").strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "vintagestory-server.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.setdefault("dotnetpath", "dotnet")
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Vintage Story server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(server.data.get("version") or "latest")
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Vintage Story dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if server.data["exe_name"].endswith(".dll"):
        command = [server.data.get("dotnetpath", "dotnet"), server.data["exe_name"]]
    else:
        command = ["./" + server.data["exe_name"]]
    data_path = "." if server.data.get("runtime") == "docker" else server.data["dir"]
    return (
        command + ["--dataPath", data_path],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Vintage Story using the standard shutdown command."""

    runtime_module.send_to_server(server, "\nstop\n")


def status(server, verbose):
    """Detailed Vintage Story status is not implemented yet."""


def message(server, msg):
    """Vintage Story has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Vintage Story server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Vintage Story datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir", "worldname", "servername", "version", "dotnetpath"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra={'host_dependencies': ({'id': 'dotnet', 'display_name': '.NET', 'command_key': 'dotnetpath', 'command': 'dotnet'},)},
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
