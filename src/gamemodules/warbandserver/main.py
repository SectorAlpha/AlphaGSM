"""Mount & Blade: Warband dedicated server lifecycle helpers."""

import os
import shutil

from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
import utils.proton as proton
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from utils.platform_info import IS_LINUX

WARBAND_DEFAULT_VERSION = "1.174"
WARBAND_INSTALL_SUBDIR = "Mount&Blade Warband Dedicated"
WARBAND_DEFAULT_EXE = os.path.join(WARBAND_INSTALL_SUBDIR, "mb_warband_dedicated.exe")
WARBAND_URL_TEMPLATE = "https://download.taleworlds.com/mb_warband_dedicated_%s.zip"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Mount and Blade: Warband in",
)
command_descriptions = {}
command_functions = {}
config_sync_keys = ("port", "maxplayers")
max_stop_wait = 1


def _download_version_token(version):
    """Return the official download token for a Warband version string."""

    return str(version).replace(".", "")


def _sample_battle_path(server):
    """Return the managed Warband sample config path."""

    return os.path.join(server.data["dir"], WARBAND_INSTALL_SUBDIR, "Sample_Battle.txt")


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows Warband executable for headless Linux hosts."""

    wrapped = proton.wrap_command(command, wineprefix=wineprefix)
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = [
        arg
        for arg in wrapped
        if not (arg.startswith("DISPLAY=") or arg.startswith("WINEDLLOVERRIDES="))
    ]
    return ["xvfb-run", "-a", *wrapped]


def resolve_download(version=None):
    """Resolve the official Warband dedicated server zip URL.

    TaleWorlds fronts the public Warband page with a Cloudflare challenge, so
    AlphaGSM uses the last verified direct archive instead of scraping the page
    during setup.
    """

    if version in (None, "", "latest"):
        version = WARBAND_DEFAULT_VERSION
    return version, WARBAND_URL_TEMPLATE % (_download_version_token(version),)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name=None,
):
    """Collect and store configuration values for a Warband server."""

    server.data.setdefault("maxplayers", "64")
    server.data.setdefault("backupfiles", ["Modules", "Configs"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Modules", "Configs"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 7240)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Warband server: [%s] " % (dir,)).strip()
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
        inp = input("Direct archive URL for the Warband server: [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "warband-dedicated.zip"
    if exe_name is None:
        exe_name = WARBAND_DEFAULT_EXE
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Warband server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_archive(server, detect_compression(server.data["download_name"]))


def sync_server_config(server):
    """Sync the managed Warband sample config with AlphaGSM settings."""

    config_path = _sample_battle_path(server)
    if not os.path.isfile(config_path):
        return
    port = int(server.data["port"])
    maxplayers = int(server.data["maxplayers"])
    replacements = {
        "set_port": "set_port %s" % (port,),
        "set_steam_port": "set_steam_port %s" % (port + 1,),
        "set_max_players": "set_max_players %s %s" % (maxplayers, maxplayers),
    }
    with open(config_path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    updated_lines = []
    seen = set()
    for line in lines:
        stripped = line.strip()
        replaced = False
        for key, value in replacements.items():
            if stripped.startswith(key):
                updated_lines.append(value + "\n")
                seen.add(key)
                replaced = True
                break
        if not replaced:
            updated_lines.append(line)
    for key, value in replacements.items():
        if key not in seen:
            updated_lines.append(value + "\n")
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.writelines(updated_lines)


def prestart(server):
    """Sync Warband's sample config before launching the server."""

    sync_server_config(server)


def get_start_command(server):
    """Build the command used to launch a Warband dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    working_dir = os.path.dirname(exe_path) or server.data["dir"]
    cmd = [
        os.path.basename(server.data["exe_name"]),
        "-r",
        "Sample_Battle.txt",
        "-m",
        "Native",
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(cmd, wineprefix=server.data.get("wineprefix"))
    return cmd, working_dir


def do_stop(server, j):
    """Stop Warband using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Warband status is not implemented yet."""


def message(server, msg):
    """Warband has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Warband server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Warband datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("url", "download_name", "exe_name", "dir", "version"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
