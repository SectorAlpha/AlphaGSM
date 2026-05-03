"""Palworld dedicated server lifecycle helpers."""

import os
import shutil

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import OptSpec

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2394010
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port to use for the Palworld server",
    "The directory to install Palworld in",
    setup_options=(
        OptSpec(
            "c",
            ["community"],
            "Start the server in community server mode.",
            "publiclobby",
            None,
            True,
        ),
    ),
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Palworld dedicated server to the latest version.",
    "Restart the Palworld dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="PalServer.sh", publiclobby=False):
    """Collect and store configuration values for a Palworld server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"publiclobby": bool(publiclobby)})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Pal/Saved", "PalWorldSettings.ini", "PalServer.sh"],
        targets=["Pal/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=8211,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", str(int(server.data["port"]) + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Palworld server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _settings_paths(server):
    """Return the default and active Palworld settings paths."""

    base_dir = os.path.join(server.data["dir"], "Pal", "Saved", "Config", "LinuxServer")
    return (
        os.path.join(server.data["dir"], "DefaultPalWorldSettings.ini"),
        os.path.join(base_dir, "PalWorldSettings.ini"),
    )


def _finalize_install_layout(server):
    """Create the active Palworld settings file from the shipped default."""

    default_settings, active_settings = _settings_paths(server)
    active_dir = os.path.dirname(active_settings)
    if not os.path.isdir(active_dir):
        os.makedirs(active_dir)
    if os.path.isfile(default_settings) and not os.path.isfile(active_settings):
        shutil.copy2(default_settings, active_settings)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Palworld server files and prepare the settings file."""

    _base_install(server)
    _finalize_install_layout(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Palworld server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Palworld server."


def get_start_command(server):
    """Build the command used to launch a Palworld dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        "./" + server.data["exe_name"],
        "-port=%s" % (server.data["port"],),
        "-queryport=%s" % (server.data["queryport"],),
    ]
    if server.data.get("publiclobby"):
        cmd.append("-publiclobby")
    return cmd, server.data["dir"]


def get_query_address(server):
    """Palworld uses Steam A2S on the dedicated queryport."""
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""
    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def do_stop(server, j):
    """Send the standard shutdown command to Palworld."""

    screen.send_to_server(server.name, "\nShutdown 1\n")


def status(server, verbose):
    """Detailed Palworld status is not implemented yet."""


def message(server, msg):
    """Palworld has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Palworld server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def _parse_bool_setting(_server, raw_value):
    """Normalize a user-supplied boolean datastore value."""

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ServerError("Unsupported value")


def checkvalue(server, key, *value):
    """Validate supported Palworld datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("exe_name", "dir", "queryport"),
        custom_handlers={"publiclobby": _parse_bool_setting},
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
)
