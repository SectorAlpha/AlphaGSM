"""Call of Duty 4 dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

COD4_SERVER_URL = "https://0day.icculus.org/cod/cod4-linux-server-06282008.tar.bz2"
COD4_SERVER_NAME = "cod4-linux-server-06282008.tar.bz2"

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Call of Duty 4 in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "moddir", "startmap")
_quake_launch_schema = gamemodule_common.build_quake_setting_schema(
    include_fs_game=True,
    game_key="moddir",
    game_description="The active Call of Duty 4 mod directory.",
    fs_game_tokens=("+set", "fs_game"),
    port_tokens=("+set", "net_port"),
    hostname_tokens=("+set", "sv_hostname"),
    hostname_before_port=True,
)
setting_schema = {
    "fs_game": SettingSpec(
        canonical_key="moddir",
        description=_quake_launch_schema["fs_game"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="moddir",
        launch_arg_tokens=_quake_launch_schema["fs_game"].launch_arg_tokens,
        examples=_quake_launch_schema["fs_game"].examples,
    ),
    "hostname": SettingSpec(
        canonical_key="hostname",
        description=_quake_launch_schema["hostname"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="hostname",
        launch_arg_tokens=_quake_launch_schema["hostname"].launch_arg_tokens,
    ),
    "port": _quake_launch_schema["port"],
    "startmap": SettingSpec(
        canonical_key="startmap",
        aliases=_quake_launch_schema["startmap"].aliases,
        description=_quake_launch_schema["startmap"].description,
        apply_to=("datastore", "launch_args", "native_config"),
        native_config_key="startmap",
        launch_arg_tokens=_quake_launch_schema["startmap"].launch_arg_tokens,
    ),
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="cod4_lnxded"):
    """Collect and store configuration values for a Call of Duty 4 server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "moddir": "main",
            "startmap": "mp_crash",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["main", "mods"],
        targets=["main", "mods"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28960,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Call of Duty 4 server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=COD4_SERVER_URL,
        default_name=COD4_SERVER_NAME,
        prompt="Direct archive URL for the Call of Duty 4 server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the Call of Duty 4 server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = COD4_SERVER_URL
        server.data.setdefault("download_name", COD4_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)


def sync_server_config(server):
    """Rewrite the managed Call of Duty 4 server.cfg values from datastore state."""

    moddir = str(server.data.get("moddir", "main"))
    config_dir = os.path.join(server.data["dir"], moddir)
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "server.cfg")
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "hostname": "AlphaGSM %s" % (server.name,),
            "moddir": "main",
            "startmap": "mp_crash",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            '"%s"' % (str(current_value),)
            if spec.canonical_key == "hostname"
            else str(current_value)
        ),
    )
    rewrite_equals_config(config_path, config_values)


def get_start_command(server):
    """Build the command used to launch a Call of Duty 4 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    launch_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return (
        ["./" + server.data["exe_name"], *launch_args],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Call of Duty 4 using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Report Call of Duty 4 server status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


def message(server, msg):
    """Call of Duty 4 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Call of Duty 4 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Call of Duty 4 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("url", "download_name", "exe_name", "dir", "moddir", "startmap", "hostname"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
