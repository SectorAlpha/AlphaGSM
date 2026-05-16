"""GTA FiveM dedicated server lifecycle helpers."""

import os
import re
import urllib.request

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

CFX_ARTIFACTS_BASE = "https://runtime.fivem.net/artifacts/fivem/build_proot_linux/master"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The game port to use for the FiveM server",
    "The directory to install FiveM in",
    version_option=gamemodule_common.STANDARD_ARTIFACT_VERSION_OPTION,
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def resolve_download(version=None):
    """Resolve a FiveM Linux artifact download URL."""

    if version in (None, "", "latest"):
        request = urllib.request.Request(
            CFX_ARTIFACTS_BASE + "/",
            headers={"User-Agent": "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"},
        )
        with urllib.request.urlopen(request) as response:
            page = response.read().decode("utf-8")
        match = re.search(
            r'LATEST RECOMMENDED.*?href="\.?/?(\d+-[a-f0-9]+)/fx\.tar\.xz"',
            page,
            re.DOTALL,
        )
        if match is None:
            raise ServerError("Unable to determine latest recommended FiveM artifact version")
        version = match.group(1)
    url = "%s/%s/fx.tar.xz" % (CFX_ARTIFACTS_BASE, version)
    return version, url


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="opt/cfx-server/run.sh",
):
    """Collect and store configuration values for a FiveM server."""

    server.data.setdefault("backupfiles", ["server-data", "citizen", "cache"])
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["server-data", "citizen", "cache"],
        targets=["server-data", "citizen"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=30120,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the FiveM server:",
    )
    gamemodule_common.configure_resolved_download_source(
        server,
        ask,
        version=version,
        url=url,
        download_name=download_name,
        resolve_download=resolve_download,
        prompt="Direct archive URL for the FiveM server:",
        default_name="fx.tar.xz",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the FiveM server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", "fx.tar.xz")
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a FiveM dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "+set",
            "sv_port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop FiveM by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed FiveM status is not implemented yet."""


def message(server, msg):
    """FiveM has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a FiveM server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported FiveM datastore edits."""

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
