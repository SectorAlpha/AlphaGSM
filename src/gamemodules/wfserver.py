"""Warfork dedicated server lifecycle helpers."""

import os

import screen
import server.runtime as runtime_module
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1136510
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Warfork in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Warfork dedicated server to the latest version.",
    "Restart the Warfork dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "hostname")
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "sv_hostname"),
        port_native_config_key="net_port",
        hostname_native_config_key="sv_hostname",
        include_bind_address=True,
        hostname_before_port=True,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="wf_server.x86_64"):
    """Collect and store configuration values for a Warfork server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "fs_game": "basewf",
            "hostname": "AlphaGSM %s" % (server.name,),
            "startmap": "wfa1",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["basewf"],
        targets=["basewf"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=44400,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Warfork server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def sync_server_config(server):
    """Write managed Warfork config values into the autoexec file."""

    autoexec_dir = os.path.join(server.data["dir"], "basewf")
    os.makedirs(autoexec_dir, exist_ok=True)
    autoexec_path = os.path.join(autoexec_dir, "dedicated_autoexec.cfg")
    managed_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "port": 44400,
            "hostname": "AlphaGSM %s" % (server.name,),
        },
        require_explicit_key=True,
    )
    port = int(managed_values["net_port"])
    hostname = managed_values["sv_hostname"]
    with open(autoexec_path, "w", encoding="utf-8") as fh:
        fh.write(f'set net_port {port}\n')
        fh.write('set sv_hostname "%s"\n' % (hostname.replace('"', '\\"'),))


def _validate_startmap(server, startmap):
    """Validate a map name against installed map files when available."""

    server_dir = server.data.get("dir")
    fs_game = server.data.get("fs_game", "basewf")
    if not server_dir:
        return startmap

    candidate_dirs = [
        os.path.join(server_dir, fs_game, "maps"),
        os.path.join(server_dir, "basewf", "maps"),
    ]
    existing_map_dirs = [path for path in candidate_dirs if os.path.isdir(path)]
    if not existing_map_dirs:
        return startmap

    available_maps = set()
    for maps_dir in existing_map_dirs:
        for entry in os.listdir(maps_dir):
            if entry.lower().endswith(".bsp"):
                available_maps.add(os.path.splitext(entry)[0])

    if not available_maps or startmap in available_maps:
        return startmap

    sample = ", ".join(sorted(available_maps)[:10])
    raise ServerError(
        "Unsupported map '%s'. Available installed maps include: %s"
        % (startmap, sample)
    )


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Warfork server files via SteamCMD."""

    _base_install(server)
    # SteamCMD ships a basewf/dedicated_autoexec.cfg that hard-codes
    # net_port 44400. Overwrite it with the configured port after install.
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Warfork server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Warfork server."


def get_start_command(server):
    """Build the command used to launch a Warfork dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        defaults={"bindaddress": "0.0.0.0"},
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
        server.data["dir"],
    )


def get_runtime_requirements(server):
    """Return Docker runtime metadata for SteamCMD-backed Linux-native servers."""

    requirements = {
        "engine": "docker",
        "family": "steamcmd-linux",
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
                "protocol": "udp",
            }
        ]
    return requirements


def get_container_spec(server):
    """Return the Docker launch spec for Warfork."""

    cmd, _cwd = get_start_command(server)
    requirements = get_runtime_requirements(server)
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": cmd,
    }


def get_query_address(server):
    """Warfork uses the Quake3/QFusion UDP getstatus query on the game port."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def get_info_address(server):
    """Return the Quake-format address used by the info command."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "quake")


def do_stop(server, j):
    """Stop Warfork using the standard quit command."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed Warfork status is not implemented yet."""


def message(server, msg):
    """Warfork has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Warfork server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Warfork datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("fs_game", "hostname", "exe_name", "dir"),
        resolved_handlers={
            "startmap": lambda active_server, *values: _validate_startmap(active_server, str(values[0]))
        },
        backup_module=backup_utils,
    )
