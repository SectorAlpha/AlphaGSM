"""Xonotic dedicated server lifecycle helpers."""

import os
import re
import urllib.request

from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

XONOTIC_DOWNLOAD_PAGE = "https://xonotic.org/download/"
XONOTIC_DOWNLOAD_TEMPLATE = "https://dl.xonotic.org/xonotic-%s.zip"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Xonotic in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def _get_managed_server_cfg_paths(server):
    """Return the candidate server.cfg paths Xonotic may require."""

    install_root_cfg = os.path.join(server.data["dir"], "data", "server.cfg")
    userdir = server.data.get("userdir", "")
    if userdir in ("", "."):
        return [install_root_cfg]
    userdir_cfg = os.path.join(server.data["dir"], userdir, "data", "server.cfg")
    if os.path.normpath(userdir_cfg) == os.path.normpath(install_root_cfg):
        return [install_root_cfg]
    return [install_root_cfg, userdir_cfg]


def _write_managed_server_cfg(server):
    """Write a minimal dedicated config where Xonotic expects it."""

    cfg_lines = [
        f'hostname "{server.data["hostname"]}"',
        f'g_gametype "{server.data["gametype"]}"',
        "",
    ]
    cfg_body = "\n".join(cfg_lines)
    for server_cfg in _get_managed_server_cfg_paths(server):
        os.makedirs(os.path.dirname(server_cfg), exist_ok=True)
        with open(server_cfg, "w", encoding="utf-8") as fh:
            fh.write(cfg_body)


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
    _write_managed_server_cfg(server)


def prestart(server):
    """Refresh the managed server.cfg before each launch."""

    _write_managed_server_cfg(server)


def get_start_command(server):
    """Build the command used to launch a Xonotic dedicated server."""

    launcher_path = os.path.join(server.data["dir"], "server", "server_linux.sh")
    if not os.path.isfile(launcher_path):
        raise ServerError("Dedicated launcher not found")
    return (
        [
            "./server/server_linux.sh",
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

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Xonotic status is not implemented yet."""


def message(server, msg):
    """Xonotic has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Xonotic server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Xonotic datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=(
            "url",
            "download_name",
            "exe_name",
            "dir",
            "userdir",
            "gametype",
            "hostname",
            "version",
        ),
        backup_module=backup_utils,
    )


def get_query_address(server):
    """Return the Quake UDP query address for Xonotic (DarkPlaces engine).

    Xonotic uses the Quake III / DarkPlaces getstatus UDP protocol,
    not the Source Engine A2S protocol.
    """
    return "127.0.0.1", server.data["port"], "quake"


def get_info_address(server):
    """Return the Quake UDP info address for Xonotic (same as query address)."""
    return "127.0.0.1", server.data["port"], "quake"

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='quake-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='quake-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
