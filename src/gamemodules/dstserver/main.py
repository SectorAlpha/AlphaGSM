"""Don't Starve Together dedicated server lifecycle helpers."""

import configparser
import io
import os

import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common
from server.modsupport.native_workshop import (
    build_native_workshop_support, safe_server_path, write_managed_text,
)
from .workshop import apply_workshop_configuration

steam_app_id = 343050
steam_anonymous_login_possible = True
workshop_app_id = 322330
MOD_SUPPORT = build_native_workshop_support(
    game_label="Don't Starve Together", workshop_app_id=workshop_app_id,
    apply_callback=apply_workshop_configuration,
)

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Don't Starve Together in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Don't Starve Together dedicated server to the latest version.",
    "Restart the Don't Starve Together dedicated server.",
)
command_functions = {}
commands += MOD_SUPPORT.commands
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions.update(MOD_SUPPORT.command_functions)
max_stop_wait = 1
config_sync_keys = ("port", "queryport", "authport")


def _cluster_config_parts(server):
    """Return contained names for the selected native cluster and shard."""
    parts = [server.data.get("confdir", "DoNotStarveTogether"),
             server.data.get("cluster", server.name), server.data.get("shard", "Master")]
    if any(not isinstance(part, str) or part in ("", ".", "..") or "/" in part or "\\" in part
           or any(ord(character) < 32 for character in part) for part in parts):
        raise ServerError("DST confdir, cluster and shard must be contained directory names")
    return parts


def sync_server_config(server):
    """Sync native shard ports while preserving supplied cluster credentials."""
    relative = "/".join(_cluster_config_parts(server)) + "/server.ini"
    path = safe_server_path(server, relative)
    if not path.is_file():
        return
    config = configparser.ConfigParser(interpolation=None)
    try:
        config.read_string(path.read_text(encoding="utf-8-sig"))
    except configparser.Error as exc:
        raise ServerError("Invalid DST shard server.ini") from exc
    values = {"NETWORK": {"server_port": server.data["port"]},
              "STEAM": {"master_server_port": server.data.get("queryport", 27016),
                        "authentication_port": server.data.get("authport", 8766)}}
    for section, settings in values.items():
        if not config.has_section(section):
            config.add_section(section)
        for key, value in settings.items():
            config.set(section, key, str(value))
    text = io.StringIO()
    config.write(text)
    write_managed_text(server, relative, text.getvalue())


def get_query_address(server):
    """Query DST on its Steam master-server port, separately from gameplay."""
    return runtime_module.resolve_query_host(server), int(server.data.get("queryport", 27016)), "a2s"


def get_info_address(server):
    """Use DST's Steam A2S endpoint for detailed server information."""
    return get_query_address(server)


def get_provider_requirements(server):
    """Declare the file-backed Klei token needed for authenticated startup."""
    parts = _cluster_config_parts(server)
    return [{
        "provider": "klei", "kind": "token", "keys": (),
        "path": "/".join(parts[:2]) + "/cluster_token.txt",
        "required_for": ("start",), "support_category": "provider-token",
        "summary": "a valid Klei cluster token and cluster configuration",
        "actions": (
            "Place a nonempty cluster_token.txt under <install_dir>/<confdir>/<cluster>/",
            "Place cluster.ini under <install_dir>/<confdir>/<cluster>/",
            f"Place {parts[2]}/server.ini under <install_dir>/<confdir>/<cluster>/",
            "Retry start once those files are present",
        ),
        "docs_slug": "dstserver",
    }]


def _assert_cluster_config_present(server):
    """Validate supplied files without reading or exposing the provider token."""
    requirements = get_provider_requirements(server)
    token = safe_server_path(server, requirements[0]["path"])
    if not token.is_file() or token.stat().st_size == 0:
        gamemodule_common.validate_provider_requirements(
            "dstserver", server, phase="start", requirements=requirements,
        )
    parts = _cluster_config_parts(server)
    paths = ("/".join(parts[:2]) + "/cluster.ini", "/".join(parts) + "/server.ini")
    if not all(safe_server_path(server, path).is_file() for path in paths):
        gamemodule_common.raise_auth_requirement(
            "dstserver", requirements[0]["summary"],
            actions=requirements[0]["actions"], docs_slug="dstserver",
        )


def configure(server, ask, port=None, dir=None, *, exe_name="bin64/dontstarve_dedicated_server_nullrenderer_x64"):
    """Collect and store configuration values for a Don't Starve Together server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "cluster": server.name,
            "shard": "Master",
            "confdir": "DoNotStarveTogether",
            "queryport": 27016,
            "authport": 8766,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DoNotStarveTogether"],
        targets=["DoNotStarveTogether"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=10999,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Don't Starve Together server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    MOD_SUPPORT.ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


def prestart(server):
    """Apply native Workshop declarations before launching the selected shard."""
    sync_server_config(server)
    mods = MOD_SUPPORT.ensure_mod_state(server)
    if mods.get('autoapply', True):
        MOD_SUPPORT.apply_configured_mods(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Don't Starve Together server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Don't Starve Together server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Don't Starve Together server."


def get_start_command(server):
    """Build the command used to launch a DST dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    _assert_cluster_config_present(server)
    return (
        [
            "./" + server.data["exe_name"],
            "-console",
            "-cluster",
            server.data["cluster"],
            "-shard",
            server.data["shard"],
            "-persistent_storage_root",
            server.data["dir"],
            "-conf_dir",
            server.data["confdir"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop DST using the standard c_shutdown command."""

    runtime_module.send_to_server(server, "\nc_shutdown(true)\n")


def status(server, verbose):
    """Detailed DST status is not implemented yet."""


def message(server, msg):
    """DST has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a DST server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported DST datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] in config_sync_keys:
        try:
            port = int(value[0])
            if not 1 <= port <= 65535:
                raise ValueError("Port outside valid range")
            return port
        except (TypeError, ValueError) as exc:
            raise ServerError("DST ports must be integers between 1 and 65535") from exc
    if key[0] in ("cluster", "shard", "confdir", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'udp'},
                          {'key': 'authport', 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'udp'},
                          {'key': 'authport', 'protocol': 'udp'}),
        stdin_open=True,
)
