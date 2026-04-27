"""Identity dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The game port to use for the Identity server",
    "The directory to install Identity in",
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
    exe_name="IdentityServer.x86_64",
):
    """Collect and store configuration values for an Identity server."""

    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Config", "Saves", "Logs"],
        targets=["Config", "Saves", "Logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Identity server:",
    )
    if url is not None:
        server.data["url"] = url
    elif "url" not in server.data and ask:
        inp = input("Direct archive URL for the Identity server: ").strip()
        if inp:
            server.data["url"] = inp
    gamemodule_common.configure_download_source(
        server,
        ask=False,
        url=server.data.get("url"),
        download_name=download_name,
        default_name="identity-server.zip",
        prompt="",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the Identity server archive."""

    if "url" not in server.data or not server.data["url"]:
        raise ServerError("A direct download URL is required for this server")
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch an Identity dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "-port", str(server.data["port"])],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Identity by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Identity status is not implemented yet."""


def message(server, msg):
    """Identity has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Identity server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Identity datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("url", "download_name", "exe_name", "dir"),
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
