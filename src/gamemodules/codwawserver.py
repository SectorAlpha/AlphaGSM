"""Call of Duty: World at War dedicated server lifecycle helpers."""

import os

import screen
from server import ServerError
from server.settable_keys import build_launch_arg_values, build_native_config_values
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils
from utils.simple_kv_config import rewrite_equals_config

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Call of Duty: World at War in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("hostname", "moddir", "startmap")
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        game_key="moddir",
        game_description="The active Call of Duty: World at War mod directory.",
        fs_game_tokens=("+set", "fs_game"),
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "sv_hostname"),
        hostname_before_port=True,
    ),
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="codwaw_lnxded"):
    """Collect and store configuration values for a COD: World at War server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "moddir": "main",
            "startmap": "mp_airfield",
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
        prompt="Where would you like to install the Call of Duty: World at War server:",
    )
    default_url = "https://www.ausgamers.com/files/download/48744/call-of-duty-world-at-war-dedicated-linux-server-files-v17"
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=default_url,
        default_name="codwaw-lnxded-1.7-11182009.tar.bz2",
        prompt="Direct archive URL for the Call of Duty: World at War server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the COD: World at War server archive."""

    if "url" not in server.data or not server.data["url"]:
        raise ServerError("A direct download URL is required for this server")
    install_archive(server, detect_compression(server.data["download_name"]))
    sync_server_config(server)


def sync_server_config(server):
    """Rewrite the managed COD: World at War server.cfg values from datastore state."""

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
            "startmap": "mp_airfield",
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
    """Build the command used to launch a COD: World at War dedicated server."""

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
    """Stop COD: World at War using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Report COD: World at War server status information."""
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))


def message(server, msg):
    """COD: World at War has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a COD: World at War server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported COD: World at War datastore edits."""

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
