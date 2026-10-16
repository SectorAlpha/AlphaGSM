"""Project Zomboid dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from server.modsupport.native_workshop import build_native_workshop_support
from . import workshop
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 380870
steam_anonymous_login_possible = True
workshop_app_id = workshop.WORKSHOP_APP_ID
MOD_SUPPORT = build_native_workshop_support(
    game_label="Project Zomboid",
    workshop_app_id=workshop_app_id,
    apply_callback=workshop.apply_workshop_mods,
)
config_sync_keys = ("port", "queryport", "servername")
sync_server_config = workshop.sync_server_config

commands = ("update", "restart") + MOD_SUPPORT.commands
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The default game port to store for this server",
    "The directory to install Project Zomboid in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Project Zomboid dedicated server to the latest version.",
    "Restart the Project Zomboid dedicated server.",
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions = dict(MOD_SUPPORT.command_functions)
setting_schema = {
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Server admin password.",
        secret=True,
    ),
}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="start-server.sh"):
    """Collect and store configuration values for a Project Zomboid server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": server.name,
            "adminpassword": "alphagsm",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Zomboid", "Server", "start-server.sh"],
        targets=["Zomboid", "Server"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=16261,
        prompt="Please specify the port to use for this server:",
    )
    # Keep the native direct-connection listener in the claimed port group.
    server.data.setdefault("queryport", int(server.data["port"]) + 1)
    MOD_SUPPORT.ensure_mod_state(server)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Project Zomboid server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def autoapply_configured_mods(server):
    """Reconcile native activation only when automatic application is enabled."""
    if MOD_SUPPORT.ensure_mod_state(server)["autoapply"]:
        MOD_SUPPORT.apply_configured_mods(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    post_download_hook=autoapply_configured_mods,
)
install.__doc__ = "Download the Project Zomboid server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    post_download_hook=autoapply_configured_mods,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Project Zomboid dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-cachedir=./Zomboid",
            "-servername",
            str(server.data["servername"]),
            "-adminpassword",
            str(server.data["adminpassword"]),
            "-port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def prestart(server):
    """Reconcile native config and Workshop intent before each launch."""
    sync_server_config(server)
    autoapply_configured_mods(server)


def get_query_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", 16262)), "udp")


def get_info_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return get_query_address(server)


def do_stop(server, j):
    """Send the standard quit command to Project Zomboid."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Project Zomboid status is not implemented yet."


def message(server, msg):
    """Project Zomboid has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Project Zomboid server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Project Zomboid datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("servername", "adminpassword", "exe_name", "dir"),
        custom_handlers={"servername": workshop.validate_servername},
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
