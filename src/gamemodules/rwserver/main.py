"""Rising World dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 339010
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Rising World in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Rising World dedicated server to the latest version.",
    "Restart the Rising World dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="server.jar", javapath="java"):
    """Collect and store configuration values for a Rising World server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "world": server.name,
            "javapath": javapath,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["world", "plugins", "server.properties", "server.jar"],
        targets=["world", "plugins", "server.properties"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=4254,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Rising World server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Rising World server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Rising World server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Rising World server."


def get_start_command(server):
    """Build the command used to launch a Rising World dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            server.data["javapath"],
            "-jar",
            server.data["exe_name"],
            "--server",
            server.data["world"],
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Rising World using the standard console command."""

    screen.send_to_server(server.name, "\nstop\n")


def status(server, verbose):
    """Detailed Rising World status is not implemented yet."""


def message(server, msg):
    """Rising World has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Rising World server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Rising World datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("servername", "world", "javapath", "exe_name", "dir"),
        backup_module=backup_utils,
    )

def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env={
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        },
        extra={"java": int(java_major)},
    )

def get_container_spec(server):
    requirements = get_runtime_requirements(server)
    return runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'tcp'},),
        env=requirements.get("env", {}),
        stdin_open=True,
        tty=True,
    )
