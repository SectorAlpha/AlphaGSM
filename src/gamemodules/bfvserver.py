"""Battlefield Vietnam dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

BFV_SERVER_URL = "https://files.gamefront.com/bfvlindedv11200407261438run/;3957406;/fileinfo.html"
BFV_SERVER_NAME = "bfvlindedv1.120040726.1438.run"

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Battlefield Vietnam in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="bfvietnam_lnxded"):
    """Collect and store configuration values for a Battlefield Vietnam server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "operation_hastings",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Mods/BFVietnam"],
        targets=["Mods/BFVietnam"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=15567,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Battlefield Vietnam server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=BFV_SERVER_URL,
        default_name=BFV_SERVER_NAME,
        prompt="Direct archive URL for the Battlefield Vietnam server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the Battlefield Vietnam server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = BFV_SERVER_URL
        server.data.setdefault("download_name", BFV_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Battlefield Vietnam dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "+statusMonitor",
            "1",
            "+map",
            server.data["startmap"],
            "+port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Battlefield Vietnam by interrupting the foreground process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Battlefield Vietnam status is not implemented yet."""


def message(server, msg):
    """Battlefield Vietnam has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Battlefield Vietnam server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Battlefield Vietnam datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir", "startmap", "hostname"),
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
