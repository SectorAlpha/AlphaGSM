"""Assetto Corsa dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from utils.settings import settings

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 302550
steam_anonymous_login_possible = False

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Assetto Corsa in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Assetto Corsa dedicated server to the latest version.",
    "Restart the Assetto Corsa dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="acServer"):
    """Collect and store configuration values for an Assetto Corsa server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "httpport": "8081",
            "udpport": "9600",
            "configfile": "cfg/server_cfg.ini",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["cfg", "content", "results"],
        targets=["cfg", "content", "results"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=9600,
        prompt="Please specify the UDP port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Assetto Corsa server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": True},
)

def get_provider_requirements(server):
    """Declare the Steam account entitlement required to download app 302550."""

    return [{
        "provider": "steam",
        "kind": "entitlement",
        "keys": (),
        "required_for": ("setup", "update"),
        "support_category": "provider-license",
        "summary": "authenticated SteamCMD access to Assetto Corsa server app 302550",
        "actions": (
            "Set username in [downloader.steamcmd] to an entitled Steam account and complete Steam Guard authentication",
            "Use the shared SteamCMD password setting when required; do not store credentials in server datastore settings",
        ),
        "docs_slug": "acserver",
    }]


def _validate_steam_auth(server, phase):
    username = settings.user.getsection("downloader").getsection("steamcmd").get("username")
    if str(username or "").strip() and str(username).strip().lower() != "anonymous":
        return
    gamemodule_common.validate_provider_requirements(
        "acserver", server, phase=phase, requirements=get_provider_requirements(server),
    )


def install(server):
    """Download the entitled server payload using the shared SteamCMD login."""

    _validate_steam_auth(server, "setup")
    _install(server)


_update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": True},
)

def update(server, validate=False, restart=False):
    """Validate Steam credentials before stopping and updating the server."""

    _validate_steam_auth(server, "update")
    _update(server, validate=validate, restart=restart)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Assetto Corsa server."


def get_start_command(server):
    """Build the command used to launch an Assetto Corsa dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-c",
            server.data["configfile"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Assetto Corsa using the standard stop command."""

    runtime_module.send_to_server(server, "\nstop\n")


def status(server, verbose):
    """Detailed Assetto Corsa status is not implemented yet."""


def message(server, msg):
    """Assetto Corsa has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Assetto Corsa server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Assetto Corsa datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "httpport"),
        str_keys=("udpport", "configfile", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'httpport', 'protocol': 'tcp'}, {'key': 'udpport', 'protocol': 'udp'}, {'key': 'udpport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'httpport', 'protocol': 'tcp'}, {'key': 'udpport', 'protocol': 'udp'}, {'key': 'udpport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
