"""Mumble server lifecycle helpers."""

import os
import shutil

import server.runtime as runtime_module
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The port for the server to listen on", int),
            ArgSpec("DIR", "The directory to store Mumble server files in", str),
        )
    )
}
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "users", "database", "serverpassword", "welcometext")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The port the server listens on.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="port",
        examples=("64738",),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        aliases=("users",),
        description="Maximum number of simultaneous users allowed on the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        storage_key="users",
        native_config_key="users",
        examples=("100",),
    ),
    "database": SettingSpec(
        canonical_key="database",
        description="Path to the SQLite database file used by the server.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        native_config_key="database",
        examples=("mumble-server.sqlite",),
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required for administrative or restricted access.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        native_config_key="serverpassword",
        secret=True,
    ),
    "welcometext": SettingSpec(
        canonical_key="welcometext",
        description="Welcome message shown to connecting users.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        native_config_key="welcometext",
        examples=("Welcome to AlphaGSM Mumble",),
    ),
}


def _default_executable():
    """Return the preferred Mumble server executable name."""

    return shutil.which("mumble-server") or shutil.which("murmurd") or "mumble-server"


def _config_path(server):
    """Return the path to the managed Mumble configuration file."""

    return os.path.join(server.data["dir"], "mumble-server.ini")


def sync_server_config(server):
    """Write the managed Mumble configuration from datastore values."""

    config_path = _config_path(server)
    os.makedirs(server.data["dir"], exist_ok=True)
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "welcometext": "Welcome to %s" % (server.name,),
            "port": 64738,
            "users": 100,
            "database": "mumble-server.sqlite",
            "serverpassword": "",
        },
        value_transform=lambda _spec, value: str(value),
        require_explicit_key=True,
    )
    with open(config_path, "w", encoding="utf-8") as config_file:
        for key_name in ("welcometext", "port", "users", "database", "serverpassword"):
            if key_name not in config_values:
                continue
            if key_name == "serverpassword" and not config_values[key_name]:
                continue
            config_file.write("%s=%s\n" % (key_name, config_values[key_name]))


def configure(server, ask, port=None, dir=None, *, exe_name=None):
    """Collect and store configuration values for a Mumble server."""

    server.data.setdefault("welcometext", "Welcome to %s" % (server.name,))
    server.data.setdefault("users", 100)
    server.data.setdefault("database", "mumble-server.sqlite")
    server.data.setdefault("serverpassword", "")
    server.data.setdefault("backupfiles", ["mumble-server.ini", "mumble-server.sqlite"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["mumble-server.ini", "mumble-server.sqlite"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 64738)
    if ask:
        inp = input("Please specify the port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to store the Mumble server files: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name or _default_executable())
    server.data.save()
    return (), {}


def install(server):
    """Prepare the local filesystem for a Mumble server."""

    os.makedirs(server.data["dir"], exist_ok=True)
    sync_server_config(server)
    server.data.save()


def get_start_command(server):
    """Build the command used to launch a Mumble server."""

    sync_server_config(server)
    return (
        [
            server.data["exe_name"],
            "-fg",
            "-ini",
            _config_path(server),
        ],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for simple TCP/UDP services."""

    requirements = {
        "engine": "docker",
        "family": "simple-tcp",
    }
    if "dir" in server.data:
        requirements["mounts"] = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"}
        ]
    if "port" in server.data:
        requirements["ports"] = [
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "tcp",
            },
            {
                "host": int(server.data["port"]),
                "container": int(server.data["port"]),
                "protocol": "udp",
            },
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for a Mumble server."""

    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            server.data["exe_name"],
            "-fg",
            "-ini",
            "/srv/server/mumble-server.ini",
        ],
    }


def do_stop(server, j):
    """Stop Mumble by sending an interrupt to the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Mumble status is not implemented yet."""


def message(server, msg):
    """Mumble has no generic broadcast console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Mumble server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Mumble datastore edits."""

    if key and key[0] == "users":
        return gamemodule_common.handle_basic_checkvalue(
            server,
            key,
            *value,
            str_keys=("users",),
            backup_module=backup_utils,
        )

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_handlers={"maxplayers": lambda _server, *values: int(values[0])},
        raw_str_keys=("welcometext", "users", "database", "serverpassword", "exe_name", "dir"),
        backup_module=backup_utils,
    )
