"""Trackmania dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

TRACKMANIA_SERVER_URL = "http://files2.trackmaniaforever.com/TrackmaniaServer_2011-02-21.zip"
TRACKMANIA_SERVER_NAME = "TrackmaniaServer_2011-02-21.zip"

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The XML-RPC port to use for the Trackmania server",
    "The directory to install Trackmania in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    url=None,
    download_name=None,
    exe_name="TrackmaniaServer",
):
    """Collect and store configuration values for a Trackmania server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "dedicated_cfg": "dedicated_cfg.txt",
            "game_settings": "MatchSettings/Nations/NationsGreen.txt",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["GameData/Config", "UserData", "Logs"],
        targets=["GameData/Config", "UserData", "Logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=5000,
        prompt="Please specify the XML-RPC port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install Trackmania in:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=TRACKMANIA_SERVER_URL,
        default_name=TRACKMANIA_SERVER_NAME,
        prompt="Direct archive URL for the Trackmania dedicated server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the Trackmania server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = TRACKMANIA_SERVER_URL
        server.data.setdefault("download_name", TRACKMANIA_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a Trackmania dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "/dedicated_cfg=%s" % (server.data["dedicated_cfg"],),
            "/game_settings=%s" % (server.data["game_settings"],),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Trackmania by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Trackmania status is not implemented yet."""


def message(server, msg):
    """Trackmania has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Trackmania server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Trackmania datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir", "dedicated_cfg", "game_settings"),
        backup_module=backup_utils,
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
