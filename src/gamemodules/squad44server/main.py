"""Squad 44 dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from server.modsupport.native_workshop import build_native_workshop_support
from .workshop import configure_workshop

steam_app_id = 746200
steam_anonymous_login_possible = True
workshop_app_id = 736220

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Squad 44 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Squad 44 dedicated server to the latest version.",
    "Restart the Squad 44 dedicated server.",
)
command_functions = {}
_mod_support = build_native_workshop_support(
    game_label="Squad 44", workshop_app_id=workshop_app_id,
    apply_callback=configure_workshop,
)
commands += _mod_support.commands
command_args.update(_mod_support.command_args)
command_descriptions.update(_mod_support.command_descriptions)
command_functions.update(_mod_support.command_functions)
ensure_mod_state = _mod_support.ensure_mod_state
apply_configured_mods = _mod_support.apply_configured_mods
cleanup_configured_mods = _mod_support.cleanup_configured_mods
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="PostScriptumServer.sh"):
    """Collect and store configuration values for a Squad 44 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"fixedmaxplayers": "80"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["PostScriptum/Saved", "PostScriptum/ServerConfig"],
        targets=["PostScriptum/Saved", "PostScriptum/ServerConfig"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7787,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", str(server.data["port"] + 1))
    server.data.setdefault("beaconport", str(server.data["port"] + 10))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Squad 44 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
def install(server):
    """Install the server and publish desired native Workshop plugins."""
    _install(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Squad 44 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Squad 44 server."


def prestart(server):
    """Reconcile native Workshop plugins before the engine discovers them."""
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


def get_start_command(server):
    """Build the command used to launch a Squad 44 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "Port=%s" % (server.data["port"],),
            "QueryPort=%s" % (server.data["queryport"],),
            "beaconport=%s" % (server.data.get("beaconport", 15000),),
            "FIXEDMAXPLAYERS=%s" % (server.data["fixedmaxplayers"],),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the A2S query address for the Squad 44 dedicated query port."""
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def do_stop(server, j):
    """Stop Squad 44 by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def get_info_address(server):
    """Require the same native A2S endpoint as the query command."""
    return get_query_address(server)


def status(server, verbose):
    """Detailed Squad 44 status is not implemented yet."""


def message(server, msg):
    """Squad 44 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Squad 44 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Squad 44 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "beaconport", "fixedmaxplayers"),
        str_keys=("exe_name", "dir"),
    )

_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "queryport", "protocol": "udp"},
    {"key": "queryport", "protocol": "tcp"},
    {"key": "beaconport", "protocol": "udp", "default": 15000},
)
port_claim_definitions = _PORT_DEFINITIONS
_RUNTIME_EXTRA = {"run_as_host_user": True, "container_home": "/home/alphagsm"}


def get_runtime_requirements(server):
    """Declare native Linux execution and the complete claimed port set."""
    return runtime_module.build_runtime_requirements(
        server, family="steamcmd-linux", port_definitions=_PORT_DEFINITIONS,
        extra=_RUNTIME_EXTRA,
    )


def get_container_spec(server):
    """Launch the native server as the owner of the disposable install."""
    return runtime_module.build_container_spec(
        server, family="steamcmd-linux", get_start_command=get_start_command,
        port_definitions=_PORT_DEFINITIONS, extra=_RUNTIME_EXTRA, stdin_open=True,
    )
