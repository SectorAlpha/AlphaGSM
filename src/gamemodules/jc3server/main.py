"""Just Cause 3 dedicated server lifecycle helpers."""

import json
import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 619960
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Just Cause 3 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Just Cause 3 dedicated server to the latest version.",
    "Restart the Just Cause 3 dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = (
    "port",
    "queryport",
    "steamport",
    "httpport",
    "maxplayers",
    "servername",
    "host",
)


def _sync_derived_ports(server):
    """Keep JC3MP side ports aligned with the managed main port by default."""

    if "port" not in server.data:
        return
    base_port = int(server.data["port"])
    previous_base_port = int(server.data.get("_derived_port_base", base_port))
    derived_offsets = (
        ("queryport", 1),
        ("steamport", 2),
        ("httpport", 3),
    )
    for key, offset in derived_offsets:
        current_value = server.data.get(key)
        previous_default = previous_base_port + offset
        new_default = base_port + offset
        if current_value in (None, "", previous_default, str(previous_default)):
            server.data[key] = new_default
        else:
            server.data[key] = int(current_value)
    server.data["_derived_port_base"] = base_port


def _config_path(server):
    return os.path.join(server.data["dir"], "config.json")


def _default_config_payload(server):
    _sync_derived_ports(server)
    return {
        "announce": False,
        "description": "",
        "host": str(server.data.get("host", "0.0.0.0")),
        "httpPort": int(server.data["httpport"]),
        "logLevel": 7,
        "logo": "",
        "maxPlayers": int(server.data.get("maxplayers", 32)),
        "maxTickRate": 60,
        "name": str(server.data.get("servername", f"AlphaGSM {server.name}")),
        "password": "",
        "port": int(server.data["port"]),
        "queryPort": int(server.data["queryport"]),
        "requiredDLC": [],
        "steamPort": int(server.data["steamport"]),
    }


def configure(server, ask, port=None, dir=None, *, exe_name="Server"):
    """Collect and store configuration values for a Just Cause 3 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "32",
            "servername": f"AlphaGSM {server.name}",
            "host": "0.0.0.0",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["config.json", "logs", "resources", "plugins"],
        targets=["config.json", "logs", "resources", "plugins"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=4200,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Just Cause 3 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    _sync_derived_ports(server)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Just Cause 3 server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Just Cause 3 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Just Cause 3 server."


def sync_server_config(server):
    """Write AlphaGSM-managed values into JC3MP's native config.json."""

    config_path = _config_path(server)
    payload = _default_config_payload(server)
    if os.path.isfile(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                existing = json.load(handle)
        except (OSError, json.JSONDecodeError):
            existing = {}
        payload = {**existing, **payload}
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)
        handle.write("\n")


def get_start_command(server):
    """Build the command used to launch a Just Cause 3 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    sync_server_config(server)
    return (["./" + server.data["exe_name"]], server.data["dir"])


def get_query_address(server):
    """Return JC3MP's validated TCP health surface on httpPort."""

    _sync_derived_ports(server)
    return runtime_module.resolve_query_host(server), int(server.data["httpport"]), "tcp"


def get_info_address(server):
    """Return JC3MP's validated TCP info surface on httpPort."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Just Cause 3 by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Just Cause 3 status is not implemented yet."""


def message(server, msg):
    """Just Cause 3 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Just Cause 3 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Just Cause 3 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "steamport", "httpport", "maxplayers"),
        str_keys=("servername", "host", "exe_name", "dir"),
    )


def get_runtime_requirements(server):
    """Return JC3MP's native Linux Docker runtime contract."""

    mounts = None
    if "dir" in server.data:
        mounts = [
            {
                "source": server.data["dir"],
                "target": "/srv/server",
                "mode": "rw",
            },
            {
                "source": os.path.normpath(steamcmd.STEAMCMD_DIR),
                "target": CONTAINER_STEAMCMD_DIR,
                "mode": "ro",
            },
        ]
    _sync_derived_ports(server)
    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "httpport", "protocol": "tcp"},
            {"key": "queryport", "protocol": "udp"},
            {"key": "steamport", "protocol": "udp"},
            {"key": "port", "protocol": "udp"},
        ),
        mounts=mounts,
    )


def get_container_spec(server):
    """Run the native Linux server as the mounted server-directory owner."""

    requirements = get_runtime_requirements(server)
    command, _cwd = get_start_command(server)
    shell_command = " ".join(shlex.quote(part) for part in command)
    user_shell_command = "cd /srv/server && " + shell_command
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
                'id -u alphagsm >/dev/null 2>&1 || useradd -M -u 1000 -o alphagsm; '
                'mkdir -p /home/alphagsm/.steam/sdk64; '
                'chmod -R a+rwX /srv/server /home/alphagsm; '
                'ln -sfn '
                + CONTAINER_STEAMCMD_DIR
                + '/linux64/steamclient.so /home/alphagsm/.steam/sdk64/steamclient.so; '
                'export HOME=/home/alphagsm USER=alphagsm LOGNAME=alphagsm; '
                "exec runuser -u alphagsm -- sh -lc "
                + shlex.quote(user_shell_command)
            ),
        ],
    }
