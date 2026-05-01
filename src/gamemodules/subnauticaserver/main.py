"""Subnautica community-server lifecycle helpers using Nitrox."""

import os

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

NITROX_LATEST_RELEASE_API = "https://api.github.com/repos/SubnauticaNitrox/Nitrox/releases/latest"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The game port to use for the Subnautica Nitrox server",
    "The directory to install the Subnautica Nitrox server in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def resolve_download(version=None):
    """Resolve the latest Nitrox server archive."""

    def _matches(asset):
        name = asset.get("name", "").lower()
        return name.endswith(".zip") and "linux_x64" in name

    from utils.github_releases import resolve_release_asset

    return resolve_release_asset(NITROX_LATEST_RELEASE_API, _matches, version=version)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="Nitrox.Server.Subnautica",
):
    """Collect and store configuration values for a Subnautica Nitrox server."""

    server.data.setdefault("backupfiles", ["Nitrox", "Saves", "Config"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Nitrox", "Saves", "Config"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 11000)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Subnautica Nitrox server: [%s] " % (dir,)).strip()
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
        inp = input("Direct archive URL for the Subnautica Nitrox server: ").strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = (
            os.path.basename(server.data.get("url", "")) or "nitrox-server-linux.zip"
        )
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Subnautica Nitrox server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(server.data["url"]))
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Subnautica Nitrox dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "--port", str(server.data["port"])],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop the Nitrox server by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Subnautica Nitrox status is not implemented yet."""


def message(server, msg):
    """Subnautica Nitrox has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Subnautica Nitrox server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Subnautica Nitrox datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir", "version"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
