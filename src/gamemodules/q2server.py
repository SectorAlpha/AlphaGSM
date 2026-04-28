"""Quake 2 dedicated server lifecycle helpers."""

import os
import re
import subprocess as sp
import urllib.parse
import urllib.request

import downloader
import screen
import server.runtime as runtime_module
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values
from utils.archive_install import detect_compression, install_archive
from utils.archive_install import resolve_archive_root, sync_tree
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.github_releases import HTTP_USER_AGENT, read_json
from utils.gamemodules import common as gamemodule_common
from utils.simple_kv_config import rewrite_equals_config

YAMAGI_Q2_PAGE = "https://www.yamagi.org/quake2/"
YAMAGI_Q2_TAGS_API = "https://api.github.com/repos/yquake2/yquake2/tags?per_page=100"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Quake 2 in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "startmap")
_quake_launch_schema = gamemodule_common.build_quake_setting_schema(
    include_fs_game=True,
    game_key="gamedir",
    game_aliases=("game",),
    game_description="The active Quake 2 game directory.",
    fs_game_tokens=("+set", "game"),
    port_tokens=("+set", "port"),
    hostname_tokens=("+set", "hostname"),
    hostname_before_port=True,
)
setting_schema = {
    "port": _quake_launch_schema["port"],
    "fs_game": _quake_launch_schema["fs_game"],
    "hostname": SettingSpec(
        canonical_key="hostname",
        aliases=_quake_launch_schema["hostname"].aliases,
        description=_quake_launch_schema["hostname"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="hostname",
        launch_arg_tokens=_quake_launch_schema["hostname"].launch_arg_tokens,
    ),
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=_quake_launch_schema["startmap"].aliases,
        description=_quake_launch_schema["startmap"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="startmap",
        launch_arg_tokens=_quake_launch_schema["startmap"].launch_arg_tokens,
    ),
    **gamemodule_common.build_versioned_download_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
    "download_mode": SettingSpec(canonical_key="download_mode", description="How the server should be installed."),
}


def resolve_download(version=None):
    """Resolve the official Yamagi Quake II source archive."""

    if version not in (None, "", "latest"):
        tags = read_json(YAMAGI_Q2_TAGS_API)
        for tag in tags:
            tag_name = tag.get("name", "")
            if str(version) in tag_name:
                archive_url = (
                    "https://github.com/yquake2/yquake2/archive/refs/tags/%s.tar.gz"
                    % (urllib.parse.quote(tag_name, safe=""),)
                )
                return str(version), archive_url
        raise ServerError("Unable to locate the requested Yamagi Quake II version")
    request = urllib.request.Request(YAMAGI_Q2_PAGE, headers={"User-Agent": HTTP_USER_AGENT})
    with urllib.request.urlopen(request) as response:
        page = response.read().decode("utf-8")
    match = re.search(
        r'href="([^"]+)">Yamagi Quake II, Version ([0-9.]+)',
        page,
        re.IGNORECASE,
    )
    if match is None:
        raise ServerError("Unable to locate the latest Yamagi Quake II source archive")
    return match.group(2), urllib.parse.urljoin(YAMAGI_Q2_PAGE, match.group(1))


def _install_from_source(server):
    """Build q2ded from the resolved Yamagi Quake II source archive."""

    downloadpath = downloader.getpath(
        "url", (server.data["url"], server.data["download_name"], "tar.gz")
    )
    source_root = resolve_archive_root(downloadpath)
    if (
        server.data.get("current_url") != server.data["url"]
        or not os.path.isfile(os.path.join(server.data["dir"], server.data["exe_name"]))
    ):
        sp.run(["make"], cwd=source_root, check=True)
        sync_tree(source_root, server.data["dir"])
        server.data["current_url"] = server.data["url"]
        server.data.save()
    else:
        print("Skipping download")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="q2ded",
):
    """Collect and store configuration values for a Quake 2 server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("gamedir", "baseq2")
    server.data.setdefault("startmap", "q2dm1")
    server.data.setdefault("backupfiles", ["baseq2"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["baseq2"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 27910)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Quake 2 server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    if url is not None:
        server.data["url"] = url
        server.data["download_mode"] = "archive"
    elif "url" not in server.data:
        resolved_version, resolved_url = resolve_download(version=version or server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data["download_mode"] = "source-build"
    if ask and url is None:
        inp = input("Direct archive URL for the Quake 2 server override [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
            server.data["download_mode"] = "archive"
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "q2server.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the Quake 2 server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
        server.data["download_mode"] = "source-build"
    if server.data.get("download_mode") == "source-build":
        _install_from_source(server)
        sync_server_config(server)
        return
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)


def sync_server_config(server):
    """Rewrite managed Quake 2 config entries from datastore values."""

    gamedir = server.data.get("gamedir", "baseq2")
    config_dir = os.path.join(server.data["dir"], gamedir)
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "server.cfg")
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "q2dm1",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            '"%s"' % (str(current_value),)
            if spec.canonical_key == "hostname"
            else str(current_value)
        ),
    )
    rewrite_equals_config(config_path, config_values)


def get_start_command(server):
    """Build the command used to launch a Quake 2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
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
    """Return the Docker launch spec for Quake 2."""

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
    """Return the Quake UDP query address used by the q2server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the q2server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Quake 2 using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Quake 2 status is not implemented yet."""


def message(server, msg):
    """Quake 2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake 2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Quake 2 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=(
            "url",
            "download_name",
            "exe_name",
            "dir",
            "gamedir",
            "startmap",
            "hostname",
            "version",
            "download_mode",
        ),
        backup_module=backup_utils,
    )
