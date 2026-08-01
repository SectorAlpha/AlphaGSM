"""Shared helpers for Terraria-family game server modules (moved from src/gamemodules).

This file is an identical copy of the previous gamemodule helper and is
intended to live under `utils.gamemodules` so other modules can import
shared helpers without depending on `src/gamemodules`.
"""

import json
import os
import re
import shutil
import tarfile
import urllib.request

import downloader
from server import ServerError
from server.settable_keys import SettingSpec
import server.runtime as runtime_module
from utils import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common

TERRARIA_HOMEPAGE = "https://terraria.org"
TERRARIA_DOWNLOAD_TEMPLATE = (
    "https://terraria.org/api/download/pc-dedicated-server/terraria-server-%s.zip"
)
TERRARIA_DEDICATED_SERVERS_API = (
    "https://terraria.org/api/get/dedicated-servers-names"
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
setting_schema = {
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required to join the server.",
        secret=True,
    ),
}


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


def _resolve_latest_from_metadata():
    names = _read_json(TERRARIA_DEDICATED_SERVERS_API)
    if not isinstance(names, list):
        raise ValueError("Terraria dedicated-server metadata is not a list")

    for name in names:
        if not isinstance(name, str):
            continue
        match = re.fullmatch(r"terraria-server-(\d+)\.zip", name)
        if match:
            tag = match.group(1)
            return tag, TERRARIA_DOWNLOAD_TEMPLATE % tag

    raise ValueError("Terraria dedicated-server metadata has no PC server asset")


def resolve_terraria_download(version=None):
    if version not in (None, "", "latest"):
        return version, TERRARIA_DOWNLOAD_TEMPLATE % (_version_to_tag(version),)

    try:
        tag, url = _resolve_latest_from_metadata()
        return ".".join(tag), url
    except (OSError, TypeError, ValueError):
        # Keep the numeric probe as a compatibility fallback if the metadata
        # endpoint is temporarily unavailable.
        pass

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
    zip_assets = []
    for asset in assets:
        name = asset.get("name", "").lower()
        if not name.endswith(".zip"):
            continue
        zip_assets.append((name, asset))

    for token in ("linux-x64", "linux-x86_64", "linux-amd64"):
        for name, asset in zip_assets:
            if token in name:
                return release_data.get("tag_name"), asset["browser_download_url"]

    for name, asset in zip_assets:
        if "linux" in name and all(excluded not in name for excluded in ("arm", "osx", "win")):
            return release_data.get("tag_name"), asset["browser_download_url"]

    for name, asset in zip_assets:
        if "release" in name or "terraria" in name:
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


def _is_archive_wrapper(path):
    lower = path.lower()
    return lower.endswith((".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2", ".tar.xz", ".txz"))


def _resolve_archive_root(downloadpath):
    entries = [os.path.join(downloadpath, entry) for entry in os.listdir(downloadpath)]
    directories = [entry for entry in entries if os.path.isdir(entry)]
    files = [entry for entry in entries if os.path.isfile(entry)]
    if len(directories) == 1 and all(_is_archive_wrapper(entry) for entry in files):
        return directories[0]
    return downloadpath


def _resolve_install_source(downloadpath):
    archive_root = _resolve_archive_root(downloadpath)
    entries = [os.path.join(archive_root, entry) for entry in os.listdir(archive_root)]
    files = [entry for entry in entries if os.path.isfile(entry)]
    tar_files = [entry for entry in files if tarfile.is_tarfile(entry)]
    if len(tar_files) != 1:
        return archive_root

    extracted_root = os.path.join(archive_root, ".alphagsm-nested-archive")
    if not os.path.isdir(extracted_root):
        os.makedirs(extracted_root, exist_ok=True)
        with tarfile.open(tar_files[0]) as archive:
            archive.extractall(extracted_root)
    return _resolve_archive_root(extracted_root)


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
        _sync_tree(_resolve_install_source(downloadpath), server.data["dir"])
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
    worldpath = "Worlds" if server.data.get("runtime") == "docker" else os.path.join(server.data["dir"], "Worlds")
    cmd = [
        "./" + server.data["exe_name"],
        "-port",
        str(server.data["port"]),
        "-maxplayers",
        str(server.data["maxplayers"]),
        "-worldpath",
        worldpath,
    ]
    world_path = get_world_path(server)
    world_path = os.path.join("Worlds", server.data["world"]) if server.data.get("runtime") == "docker" else world_path
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
    if server.data["exe_name"].endswith(".dll"):
        dotnet = server.data.get("dotnetpath", "dotnet")
        cmd = [dotnet, server.data["exe_name"], "-port", str(server.data["port"])]
    else:
        cmd = ["./" + server.data["exe_name"], "-port", str(server.data["port"])]
    return cmd, server.data["dir"]


def get_start_command(server):
    raise NotImplementedError(
        "terraria.common is a helper module; call terraria.vanilla or terraria.tshock"
    )


def do_stop(server, j):
    runtime_module.send_to_server(server, "\nexit\n")


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
