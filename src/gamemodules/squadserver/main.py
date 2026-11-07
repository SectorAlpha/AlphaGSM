"""Squad dedicated server lifecycle helpers."""

import os
import re
import secrets

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from server.modsupport.native_workshop import build_native_workshop_support
from server.modsupport.native_workshop import safe_server_path, write_managed_text
from .workshop import configure_workshop

steam_app_id = 403240
steam_anonymous_login_possible = True
workshop_app_id = 393380

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Squad in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Squad dedicated server to the latest version.",
    "Restart the Squad dedicated server.",
)
command_functions = {}
_mod_support = build_native_workshop_support(
    game_label="Squad", workshop_app_id=workshop_app_id,
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
config_sync_keys = ("rconport", "adminpassword")
setting_schema = {
    "adminpassword": SettingSpec(canonical_key="adminpassword", secret=True,
                                 description="Local native RCON password."),
}


def configure(server, ask, port=None, dir=None, *, exe_name="SquadGameServer.sh"):
    """Collect and store configuration values for a Squad server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"fixedmaxplayers": "80"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["SquadGame/ServerConfig", "SquadGame/Saved"],
        targets=["SquadGame/ServerConfig", "SquadGame/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7787,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", str(server.data["port"] + 1))
    server.data.setdefault("rconport", str(server.data["port"] + 2))
    server.data.setdefault("beaconport", str(server.data["port"] + 10))
    server.data.setdefault("adminpassword", secrets.token_urlsafe(24))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Squad server:",
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
    sync_server_config(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)





restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Squad server."


def prestart(server):
    """Reconcile native Workshop plugins before the engine discovers them."""
    sync_server_config(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


def get_start_command(server):
    """Build the command used to launch a Squad dedicated server."""

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
    """Use the native EOS-era server's authenticated local RCON query."""
    return (runtime_module.resolve_query_host(server), int(server.data.get("rconport", 21114)),
            "squad_rcon")


def do_stop(server, j):
    """Stop Squad by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def get_info_address(server):
    """Require the same native RCON endpoint as the query command."""
    return get_query_address(server)


def status(server, verbose):
    """Detailed Squad status is not implemented yet."""


def message(server, msg):
    """Squad has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Squad server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Squad datastore edits."""

    if key and key[0] == "adminpassword" and (len(value) != 1 or not value[0]
                                  or any(char in value[0] for char in "\r\n\x00")):
        raise ServerError("RCON password must be nonempty and contain no line breaks")
    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "rconport", "beaconport", "fixedmaxplayers"),
        str_keys=("exe_name", "dir", "adminpassword"),
    )


def sync_server_config(server):
    """Keep native RCON settings aligned while preserving operator options."""
    install_dir = server.data.get("dir")
    if not install_dir or not os.path.isdir(install_dir):
        return
    relative = "SquadGame/ServerConfig/Rcon.cfg"
    path = safe_server_path(server, relative)
    text = ""
    if path.exists():
        with path.open("rb") as handle:
            raw = handle.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ServerError("Squad RCON configuration exceeds 1 MiB")
        text = raw.decode("utf-8-sig")
    server.data.setdefault("rconport", "21114")
    server.data.setdefault("adminpassword", secrets.token_urlsafe(24))
    password = server.data["adminpassword"]
    checkvalue(server, ["adminpassword"], password)
    values = {"IP": "0.0.0.0", "Port": str(int(server.data["rconport"])),
              "Password": password}
    lines = []
    for line in text.splitlines():
        match = re.match(r"\s*([A-Za-z]+)\s*=", line)
        if not match or match.group(1).lower() not in {key.lower() for key in values}:
            lines.append(line)
    lines.extend(f"{key}={value}" for key, value in values.items())
    written = write_managed_text(server, relative, "\n".join(lines) + "\n")
    written.chmod(0o600)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Squad server files and optionally restart the server."

_PORT_DEFINITIONS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "queryport", "protocol": "udp"},
    {"key": "queryport", "protocol": "tcp"},
    {"key": "rconport", "protocol": "tcp", "default": 21114},
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
