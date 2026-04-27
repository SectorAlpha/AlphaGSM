"""Return to Castle Wolfenstein dedicated server lifecycle helpers."""

import os

import server.runtime as runtime_module
from server import ServerError
from server.settable_keys import build_launch_arg_values
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec
from utils.github_releases import resolve_release_asset
from utils.gamemodules import common as gamemodule_common

IORTCW_LATEST_RELEASE_API = "https://api.github.com/repos/iortcw/iortcw/releases/latest"

commands = ()
command_args = gamemodule_common.build_setup_version_download_command_args(
    "The port for the server to listen on",
    "The directory to install Return to Castle Wolfenstein in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "sv_hostname"),
    ),
    **gamemodule_common.build_versioned_download_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def resolve_download(version=None):
    """Resolve an ioRTCW Linux release asset suitable for a dedicated server."""

    def _matches(asset):
        name = asset.get("name", "").lower()
        return "linux" in name and "x86_64" in name and name.endswith(".zip")

    return resolve_release_asset(IORTCW_LATEST_RELEASE_API, _matches, version=version)


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    download_name=None,
    exe_name="iowolfded.x86_64",
):
    """Collect and store configuration values for an RTCW server."""

    server.data.setdefault("hostname", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("fs_game", "main")
    server.data.setdefault("startmap", "mp_beach")
    server.data.setdefault("backupfiles", ["main"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["main"]}},
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
            inp = input("Where would you like to install the RTCW server: [%s] " % (dir,)).strip()
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
        inp = input("Direct archive URL for the RTCW server: [%s] " % (server.data["url"],)).strip()
        if inp:
            server.data["url"] = inp
    if download_name is not None:
        server.data["download_name"] = download_name
    elif "download_name" not in server.data:
        server.data["download_name"] = os.path.basename(server.data.get("url", "")) or "rtcwserver.tar.gz"
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download and install the RTCW server archive."""

    if "url" not in server.data or not server.data["url"]:
        resolved_version, resolved_url = resolve_download(version=server.data.get("version"))
        server.data["version"] = resolved_version
        server.data["url"] = resolved_url
        server.data.setdefault("download_name", os.path.basename(resolved_url))
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch an RTCW dedicated server."""

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
    """Return the Docker launch spec for RTCW."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def do_stop(server, j):
    """Stop RTCW using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed RTCW status is not implemented yet."""


def message(server, msg):
    """RTCW has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an RTCW server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported RTCW datastore edits."""

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
            "fs_game",
            "startmap",
            "hostname",
            "version",
        ),
        backup_module=backup_utils,
    )
