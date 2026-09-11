"""Longvinter dedicated server lifecycle helpers."""

import os
import shlex
import shutil

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.backups import backups as backup_utils
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1639880
steam_anonymous_login_possible = True
DEFAULT_CONFIGFILE = "Longvinter/Saved/Config/LinuxServer/Game.ini"
config_sync_keys = ("maxplayers", "servername")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Longvinter server",
    "The directory to install Longvinter in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Longvinter dedicated server to the latest version.",
    "Restart the Longvinter dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="Primary gameplay port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-Port={value}",
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum allowed players.",
        value_type="integer",
    ),
    "servername": SettingSpec(canonical_key="servername", description="Configured public server name."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="LongvinterServer.sh"):
    """Collect and store configuration values for a Longvinter server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "32",
            "servername": "Unnamed Island",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Longvinter/Saved/Config/LinuxServer", "Longvinter/Saved/SaveGames"],
        targets=["Longvinter/Saved/Config/LinuxServer", "Longvinter/Saved/SaveGames"],
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
        prompt="Where would you like to install the Longvinter server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    server.data.setdefault("configfile", DEFAULT_CONFIGFILE)
    return gamemodule_common.finalize_configure(server)


def _config_path(server):
    return os.path.join(server.data["dir"], server.data.get("configfile", DEFAULT_CONFIGFILE))


def _default_config_path(server):
    return _config_path(server) + ".default"


def sync_server_config(server):
    """Keep Longvinter's Game.ini aligned with supported AlphaGSM settings."""

    if not server.data.get("dir"):
        return
    config_path = _config_path(server)
    if not os.path.isfile(config_path):
        default_path = _default_config_path(server)
        if not os.path.isfile(default_path):
            return
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        shutil.copyfile(default_path, config_path)
    rewrite_equals_config(
        config_path,
        {
            "ServerName": server.data.get("servername", "Unnamed Island"),
            "MaxPlayers": int(server.data.get("maxplayers", 32)),
        },
    )


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Longvinter server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Longvinter server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Longvinter server."


def prestart(server):
    """Refresh Game.ini before each launch."""

    sync_server_config(server)


def get_start_command(server):
    """Build the command used to launch a Longvinter dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        {"port": setting_schema["port"]},
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        [
            "./" + server.data["exe_name"],
            *dynamic_args,
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the live Longvinter health endpoint on the gameplay UDP port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the address used by the info command."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Longvinter using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Longvinter status is not implemented yet."""


def message(server, msg):
    """Longvinter has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Longvinter server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Longvinter datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=({"key": "port", "protocol": "udp"},),
)


def get_container_spec(server):
    """Run the Linux server in Docker as the mounted server-directory owner."""

    requirements = get_runtime_requirements(server)
    command, _cwd = get_start_command(server)
    shell_command = " ".join(shlex.quote(part) for part in command)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "tty": False,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            "sh",
            "-lc",
            (
                'uid=$(stat -c %u /srv/server); '
                'gid=$(stat -c %g /srv/server); '
                'getent group "$gid" >/dev/null || groupadd -o -g "$gid" alphagsm; '
                'id -u alphagsm >/dev/null 2>&1 || useradd -M -u "$uid" -g "$gid" -o alphagsm; '
                f"exec runuser -u alphagsm -- {shell_command}"
            ),
        ],
    }
