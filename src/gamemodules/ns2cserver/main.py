"""NS2: Combat dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 313900
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the NS2: Combat server",
    "The directory to install NS2: Combat in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the NS2: Combat dedicated server to the latest version.",
    "Restart the NS2: Combat dedicated server.",
)
command_functions = {}
max_stop_wait = 1
_RUNTIME_PORTS = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "offset": 1, "protocol": "udp"},
    {"key": "httpport", "protocol": "tcp"},
)
setting_schema = {
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised server name.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-name",),
    ),
    "port": SettingSpec(
        canonical_key="port",
        description="Primary gameplay port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-port",),
    ),
    "httpuser": SettingSpec(
        canonical_key="httpuser",
        description="Web admin username.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-webuser",),
    ),
    "httppassword": SettingSpec(
        canonical_key="httppassword",
        description="Web admin password.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-webpassword",),
    ),
    "httpport": SettingSpec(
        canonical_key="httpport",
        description="Web admin port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-webport",),
    ),
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=("map",),
        description="Startup map.",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-map",),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum allowed players.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-limit",),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _config_dir(server):
    return os.path.join(server.data["dir"], server.name)


def _mod_storage_dir(server):
    return os.path.join(_config_dir(server), "Workshop")


def _log_dir(server):
    return os.path.join(server.data["dir"], "logs")


def _ensure_server_dirs(server):
    os.makedirs(_config_dir(server), exist_ok=True)
    os.makedirs(_mod_storage_dir(server), exist_ok=True)
    os.makedirs(_log_dir(server), exist_ok=True)


def configure(server, ask, port=None, dir=None, *, exe_name="ia32/ns2combatserver_linux32"):
    """Collect and store configuration values for an NS2: Combat server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "httpuser": "admin",
            "httppassword": "CHANGE_ME",
            "httpport": "8080",
            "startmap": "co_core",
            "maxplayers": "24",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=[server.name, "logs"],
        targets=[server.name, "logs"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the NS2: Combat server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=_ensure_server_dirs,
)
install.__doc__ = "Download the NS2: Combat server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=_ensure_server_dirs,
)
update.__doc__ = "Update the NS2: Combat server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the NS2: Combat server."


def get_query_address(server):
    """NS2: Combat exposes A2S one port above gameplay."""

    return runtime_module.resolve_query_host(server), int(server.data["port"]) + 1, "a2s"


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def _relative_launch_path(target, working_dir):
    relative_path = os.path.relpath(target, working_dir)
    if not relative_path.startswith("."):
        relative_path = "./" + relative_path
    return relative_path.replace(os.sep, "/")


def _path_is_within(root, path):
    try:
        return os.path.commonpath((root, path)) == root
    except ValueError:
        return False


def _validate_payload_location(server, install_dir, exe_path, *, resolve_links):
    normalize = os.path.realpath if resolve_links else os.path.abspath
    normalized_install_dir = normalize(install_dir)
    normalized_exe_path = normalize(exe_path)
    if not _path_is_within(normalized_install_dir, normalized_exe_path):
        raise ServerError("Executable target is outside the install directory")

    relative_dir = os.path.dirname(
        os.path.relpath(normalized_exe_path, normalized_install_dir)
    )
    excluded_dirs = {server.name.lower(), "workshop", "config", "logs"}
    if any(part.lower() in excluded_dirs for part in relative_dir.split(os.sep)):
        raise ServerError("Executable is not in a safe install payload directory")


def _validate_payload_executable(server, install_dir, exe_path):
    _validate_payload_location(
        server,
        install_dir,
        exe_path,
        resolve_links=False,
    )
    _validate_payload_location(
        server,
        install_dir,
        exe_path,
        resolve_links=True,
    )


def _launcher_for_executable(install_dir, exe_path):
    resolved_exe_path = os.path.realpath(exe_path)
    working_dir = os.path.dirname(resolved_exe_path) or install_dir
    if os.path.normpath(working_dir) == os.path.normpath(install_dir):
        working_dir = os.path.join(install_dir, "")
    return resolved_exe_path, "./" + os.path.basename(resolved_exe_path), working_dir


def _resolve_safe_install_launcher(server):
    install_dir = os.path.abspath(server.data["dir"])
    configured_name = server.data["exe_name"]
    if os.path.isabs(configured_name) or ".." in configured_name.split(os.sep):
        raise ServerError("Executable target is outside the install directory")
    configured_name = os.path.normpath(configured_name)
    configured_path = os.path.join(install_dir, configured_name)

    if os.path.lexists(configured_path):
        _validate_payload_location(
            server,
            install_dir,
            configured_path,
            resolve_links=False,
        )
        if not os.path.isfile(configured_path):
            raise ServerError("Configured executable is not a regular file")
        _validate_payload_executable(server, install_dir, configured_path)
        return _launcher_for_executable(install_dir, configured_path)

    basename = os.path.basename(configured_name)
    excluded_dirs = {server.name.lower(), "workshop", "config", "logs"}
    candidates = []
    for current_dir, dirnames, filenames in os.walk(install_dir):
        dirnames[:] = [
            dirname for dirname in dirnames if dirname.lower() not in excluded_dirs
        ]
        if basename not in filenames:
            continue
        candidate = os.path.join(current_dir, basename)
        if not os.path.isfile(candidate):
            continue
        _validate_payload_executable(server, install_dir, candidate)
        candidates.append(candidate)

    if not candidates:
        raise ServerError("Executable file not found in safe install payload directories")
    if len(candidates) != 1:
        raise ServerError(
            "Executable fallback is ambiguous across safe install payload directories"
        )

    return _launcher_for_executable(install_dir, candidates[0])


def get_start_command(server):
    """Build the command used to launch an NS2: Combat server."""

    _exe_path, launcher, working_dir = _resolve_safe_install_launcher(server)
    install_dir = os.path.realpath(os.path.abspath(server.data["dir"]))

    config_path = _relative_launch_path(
        os.path.join(install_dir, server.name),
        working_dir,
    )
    log_path = _relative_launch_path(
        os.path.join(install_dir, "logs"),
        working_dir,
    )
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    command = [
        launcher,
        *dynamic_args,
        "-webadmin",
        "-config_path",
        config_path,
        "-logdir",
        log_path,
        "-modstorage",
        config_path + "/Workshop",
    ]
    return command, working_dir


def do_stop(server, j):
    """Stop NS2: Combat using the console quit command."""

    runtime_module.send_to_server(server, "\nq\n")


def status(server, verbose):
    """Detailed NS2: Combat status is not implemented yet."""


def message(server, msg):
    """NS2: Combat has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an NS2: Combat server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported NS2: Combat datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "httpport", "maxplayers"),
        resolved_str_keys=("servername", "httpuser", "httppassword", "startmap", "exe_name", "dir"),
        backup_module=backup_utils,
    )


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=_RUNTIME_PORTS,
)


get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=_RUNTIME_PORTS,
    stdin_open=True,
)
