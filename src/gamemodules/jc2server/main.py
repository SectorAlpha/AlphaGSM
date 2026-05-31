"""Just Cause 2 dedicated server lifecycle helpers."""

import os
import re
import shutil

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 261140
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Just Cause 2 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Just Cause 2 dedicated server to the latest version.",
    "Restart the Just Cause 2 dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "maxplayers", "servername")


def _config_path(server):
    return os.path.join(server.data["dir"], "config.lua")


def _default_config_path(server):
    return os.path.join(server.data["dir"], "default_config.lua")


def _sync_default_scripts(server):
    default_scripts_dir = os.path.join(server.data["dir"], "default_scripts")
    scripts_dir = os.path.join(server.data["dir"], "scripts")
    if not os.path.isdir(default_scripts_dir):
        return
    os.makedirs(scripts_dir, exist_ok=True)
    for root, _dirs, files in os.walk(default_scripts_dir):
        relative_root = os.path.relpath(root, default_scripts_dir)
        target_root = scripts_dir if relative_root == "." else os.path.join(scripts_dir, relative_root)
        os.makedirs(target_root, exist_ok=True)
        for filename in files:
            source_path = os.path.join(root, filename)
            target_path = os.path.join(target_root, filename)
            if not os.path.exists(target_path):
                shutil.copy2(source_path, target_path)


def sync_server_config(server):
    """Write AlphaGSM-managed values into JC2-MP's native config.lua."""

    config_path = _config_path(server)
    default_config_path = _default_config_path(server)
    port = int(server.data.get("port", 7777))
    maxplayers = int(server.data.get("maxplayers", 64))
    servername = str(server.data.get("servername", f"AlphaGSM {server.name}"))
    if not os.path.isfile(config_path):
        if os.path.isfile(default_config_path):
            shutil.copyfile(default_config_path, config_path)
        else:
            with open(config_path, "w", encoding="utf-8") as handle:
                handle.write(
                    "Server = {\n"
                    "    MaxPlayers = 5000,\n"
                    "    BindPort = 7777,\n"
                    '    Name = "JC2-MP Server",\n'
                    "}\n"
                )
    with open(config_path, "r", encoding="utf-8") as handle:
        config_text = handle.read()
    replacements = (
        (r"(?m)^(\s*MaxPlayers\s*=\s*)\d+,", r"\g<1>{},".format(maxplayers)),
        (r"(?m)^(\s*BindPort\s*=\s*)\d+,", r"\g<1>{},".format(port)),
        (
            r'(?m)^(\s*Name\s*=\s*)".*",',
            r'\g<1>"{}",'.format(servername.replace("\\", "\\\\").replace('"', '\\"')),
        ),
    )
    for pattern, replacement in replacements:
        config_text = re.sub(pattern, replacement, config_text)
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write(config_text)
    _sync_default_scripts(server)


def configure(server, ask, port=None, dir=None, *, exe_name="Jcmp-Server"):
    """Collect and store configuration values for a Just Cause 2 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "64",
            "servername": f"AlphaGSM {server.name}",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["config.lua", "scripts"],
        targets=["config.lua", "scripts"],
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
        prompt="Where would you like to install the Just Cause 2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Just Cause 2 server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Just Cause 2 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Just Cause 2 server."


def get_start_command(server):
    """Build the command used to launch a Just Cause 2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    sync_server_config(server)
    return (["./" + server.data["exe_name"]], server.data["dir"])


def get_query_address(server):
    """Return JC2-MP's validated TCP health surface on the managed game port."""

    return runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp"


def get_info_address(server):
    """Return JC2-MP's validated TCP info surface on the managed game port."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Just Cause 2 by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Just Cause 2 status is not implemented yet."""


def message(server, msg):
    """Just Cause 2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Just Cause 2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Just Cause 2 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("servername", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        extra={"stop_mode": "docker-stop"},
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
        extra={"stop_mode": "docker-stop"},
)
