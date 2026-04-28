"""Shared helpers for Terraria-family game server modules (moved from src/gamemodules).

This file is an identical copy of the previous gamemodule helper and is
intended to live under `utils.gamemodules` so other modules can import
shared helpers without depending on `src/gamemodules`.
"""

import json
import os
import re
import shutil
import urllib.request

import downloader
import screen
from server import ServerError
from utils import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common

TERRARIA_HOMEPAGE = "https://terraria.org"
TERRARIA_DOWNLOAD_TEMPLATE = (
    "https://terraria.org/api/download/pc-dedicated-server/terraria-server-%s.zip"
)
TSHOCK_LATEST_RELEASE_API = "https://api.github.com/repos/Pryaxis/TShock/releases/latest"
HTTP_USER_AGENT = "AlphaGSM/1.0 (+https://github.com/SectorAlpha/AlphaGSM)"


commands = ()
command_args = gamemodule_common.build_setup_version_url_command_args(
    "The port for the server to listen on",
    "The directory to install Terraria in",
)
command_descriptions = {}
command_functions = {}


def _read_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        return response.read().decode("utf-8")


def _read_json(url):
    return json.loads(_read_text(url))


def _version_to_tag(version):
    return version.replace(".", "").replace("-", "")


def _head_ok(url):
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": HTTP_USER_AGENT}
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False


def resolve_terraria_download(version=None):
    if version not in (None, "", "latest"):
        return version, TERRARIA_DOWNLOAD_TEMPLATE % (_version_to_tag(version),)
    baseline = 1449
    tag = baseline
    while _head_ok(TERRARIA_DOWNLOAD_TEMPLATE % (tag + 1,)):
        tag += 1
    if not _head_ok(TERRARIA_DOWNLOAD_TEMPLATE % (tag,)):
        raise ServerError("Unable to locate the latest Terraria server download URL")
    version = ".".join(str(tag))
    return version, TERRARIA_DOWNLOAD_TEMPLATE % (tag,)


def resolve_tshock_download():
    release_data = _read_json(TSHOCK_LATEST_RELEASE_API)
    assets = release_data.get("assets", [])
    for asset in assets:
        name = asset.get("name", "").lower()
        if not name.endswith(".zip"):
            continue
        if "linux" in name or "release" in name or "terraria" in name:
            return release_data.get("tag_name"), asset["browser_download_url"]
    raise ServerError("Unable to locate a suitable TShock release asset")


def _sync_tree(source, target):
    os.makedirs(target, exist_ok=True)
    for root, dirs, files in os.walk(source):
        rel_root = os.path.relpath(root, source)
        target_root = target if rel_root == "." else os.path.join(target, rel_root)
        os.makedirs(target_root, exist_ok=True)
        for dirname in dirs:
            os.makedirs(os.path.join(target_root, dirname), exist_ok=True)
        for filename in files:
            shutil.copy2(os.path.join(root, filename), os.path.join(target_root, filename))


def _resolve_archive_root(downloadpath):
    entries = [os.path.join(downloadpath, entry) for entry in os.listdir(downloadpath)]
    directories = [entry for entry in entries if os.path.isdir(entry)]
    if len(directories) == 1:
        return directories[0]
    return downloadpath


def install_archive(server):
    if not os.path.isdir(server.data["dir"]):
        os.makedirs(server.data["dir"])
    if (
        "current_url" not in server.data
        or server.data["current_url"] != server.data["url"]
        or not os.path.isfile(os.path.join(server.data["dir"], server.data["exe_name"]))
    ):
        downloadpath = downloader.getpath(
            "url", (server.data["url"], server.data["download_name"], "zip")
        )
        _sync_tree(_resolve_archive_root(downloadpath), server.data["dir"])
        server.data["current_url"] = server.data["url"]
    else:
        print("Skipping download")
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if os.path.isfile(exe_path):
        os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    server.data.save()


def configure_base(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name,
    version=None,
    url=None,
    download_name,
    max_players=8,
    world_name="world",
    world_size=2,
    backupfiles=None,
    java_runtime=None,
):
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {
                "default": {"targets": list(backupfiles or ("Worlds", "serverconfig.txt")),},
            },
            "schedule": [("default", 0, "days")],
        }
    server.data.setdefault("backupfiles", list(backupfiles or ("Worlds", "serverconfig.txt")))
    server.data.setdefault("maxplayers", str(max_players))
    server.data.setdefault("worldname", world_name)
    server.data.setdefault("worldsize", str(world_size))
    server.data.setdefault("world", world_name + ".wld")
    server.data.setdefault("serverpassword", "")

    if port is None:
        port = server.data.get("port", 7777)
    if ask:
        inp = input(
            "Please specify the port to use for this server: [%s] " % (port,)
        ).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Terraria server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = dir

    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data["download_name"] = download_name
    server.data["version"] = version
    server.data["url"] = url
    if java_runtime is not None:
        server.data.setdefault("dotnetpath", java_runtime)
    server.data.save()
    return (), {}


def get_world_path(server):
    return os.path.join(server.data["dir"], "Worlds", server.data["world"])


def get_vanilla_start_command(server):
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        "./" + server.data["exe_name"],
        "-port",
        str(server.data["port"]),
        "-maxplayers",
        str(server.data["maxplayers"]),
        "-worldpath",
        os.path.join(server.data["dir"], "Worlds"),
    ]
    world_path = get_world_path(server)
    if os.path.isfile(world_path):
        cmd.extend(["-world", world_path])
    else:
        cmd.extend([
            "-autocreate",
            str(server.data["worldsize"]),
            "-world",
            world_path,
        ])
    if server.data.get("serverpassword"):
        cmd.extend(["-password", server.data["serverpassword"]])
    return cmd, server.data["dir"]


def get_tshock_start_command(server):
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dotnet = server.data.get("dotnetpath", "dotnet")
    cmd = [dotnet, server.data["exe_name"], "-port", str(server.data["port"])]
    return cmd, server.data["dir"]


def get_start_command(server):
    raise NotImplementedError(
        "terraria.common is a helper module; call terraria.vanilla or terraria.tshock"
    )


def do_stop(server, j):
    screen.send_to_server(server.name, "\nexit\n")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


status.__doc__ = "Detailed Terraria-family status is not implemented yet."


message = gamemodule_common.make_server_message_hook(command="say")
message.__doc__ = "Send a Terraria-family server message through the console."


def backup(server, profile=None):
    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in ("port", "worldsize"):
        return int(value[0])
    if key[0] in (
        "exe_name",
        "url",
        "version",
        "world",
        "worldname",
        "serverpassword",
        "dotnetpath",
        "dir",
    ):
        return str(value[0])
    if key[0] == "maxplayers":
        return str(int(value[0]))
    raise ServerError("Unsupported key")


def get_runtime_requirements(server):
    raise NotImplementedError("terraria.common is a helper module; call terraria.vanilla or terraria.tshock")


def get_container_spec(server):
    raise NotImplementedError("terraria.common is a helper module; call terraria.vanilla or terraria.tshock")
