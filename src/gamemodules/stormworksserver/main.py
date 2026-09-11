"""Stormworks dedicated server lifecycle helpers."""

import os

import utils.proton as proton
from server import ServerError
from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1247090
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Stormworks server",
    "The directory to install Stormworks in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Stormworks dedicated server to the latest version.",
    "Restart the Stormworks dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="server64.exe"):
    """Collect and store configuration values for a Stormworks server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "25566",
            "configfile": "server_config.xml",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["server_config.xml", "saves"],
        targets=["server_config.xml", "saves"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=25565,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Stormworks server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Explain the authenticated-install requirement for Stormworks."""

    gamemodule_common.raise_byo_requirement(
        "stormworksserver",
        "authenticated Steam or SteamCMD access to the Stormworks Dedicated Server tool",
        actions=(
            "Install the Stormworks Dedicated Server tool through a logged-in Steam client or authenticated SteamCMD workflow",
            "Stage that installed server tree into <install_dir> so server64.exe and its runtime data come from the authenticated install rather than Steam app 1247090's redirect stub",
            "Retry start once the authenticated server tree is staged in the install directory",
        ),
        docs_slug="stormworksserver",
    )


def update(server, validate=False, restart=False):
    """Explain the authenticated-install update requirement for Stormworks."""

    gamemodule_common.raise_byo_requirement(
        "stormworksserver",
        "an authenticated Stormworks Dedicated Server tool refresh",
        actions=(
            "Refresh the staged Stormworks dedicated-server files through a logged-in Steam client or authenticated SteamCMD workflow instead of using Steam app 1247090 anonymously",
            "Retry start after restaging the authenticated server tree in <install_dir>",
        ),
        docs_slug="stormworksserver",
    )


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Stormworks server."


def get_start_command(server):
    """Build the command used to launch a Stormworks dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"]]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Stormworks using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Stormworks status is not implemented yet."""


def message(server, msg):
    """Stormworks has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Stormworks server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Stormworks datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("configfile", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
