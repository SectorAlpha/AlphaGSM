"""Quake 4 dedicated server lifecycle helpers."""

import os

import screen
import server.runtime as runtime_module
from server import ServerError
from server.settable_keys import build_launch_arg_values
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

Q4_SERVER_URL = "https://cloud.quake4.net/files/quake4_linux_1.4.2.x86.run"
Q4_SERVER_NAME = "quake4_linux_1.4.2.x86.run"

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The game port for the server to listen on",
    "The directory to install Quake 4 in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "si_name"),
    ),
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="q4ded.x86"):
    """Collect and store configuration values for a Quake 4 server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "fs_game": "q4base",
            "startmap": "q4dm1",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["q4base"],
        targets=["q4base"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28004,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Quake 4 server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=Q4_SERVER_URL,
        default_name=Q4_SERVER_NAME,
        prompt="Direct archive URL for the Quake 4 server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the Quake 4 server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = Q4_SERVER_URL
        server.data.setdefault("download_name", Q4_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Quake 4 dedicated server."""

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
    """Return the Docker launch spec for Quake 4."""

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
    """Return the Quake UDP query address used by the q4server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake UDP info address used by the q4server module."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Quake 4 using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Quake 4 status is not implemented yet."""


def message(server, msg):
    """Quake 4 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Quake 4 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Quake 4 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("url", "download_name", "exe_name", "dir", "fs_game", "hostname", "startmap"),
        backup_module=backup_utils,
    )
