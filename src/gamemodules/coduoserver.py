"""Call of Duty: United Offensive dedicated server lifecycle helpers."""

import screen
from server import ServerError
from server.settable_keys import build_launch_arg_values
from utils.archive_install import detect_compression, install_archive
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

CODUO_SERVER_URL = "https://0day.icculus.org/cod/coduo-lnxded-1.51-large.tar.bz2"
CODUO_SERVER_NAME = "coduo-lnxded-1.51-large.tar.bz2"

commands = ()
command_args = gamemodule_common.build_setup_download_command_args(
    "The port for the server to listen on",
    "The directory to install Call of Duty: United Offensive in",
)
command_descriptions = {}
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_quake_setting_schema(
        include_fs_game=True,
        game_key="moddir",
        game_description="The active Call of Duty: United Offensive mod directory.",
        fs_game_tokens=("+set", "fs_game"),
        port_tokens=("+set", "net_port"),
        hostname_tokens=("+set", "sv_hostname"),
        hostname_before_port=True,
    ),
    **gamemodule_common.build_download_source_setting_schema(),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, url=None, download_name=None, exe_name="coduoded_lnxded"):
    """Collect and store configuration values for a COD: United Offensive server."""

    gamemodule_common.set_server_defaults(
        server,
        {
            "hostname": "AlphaGSM %s" % (server.name,),
            "moddir": "uo",
            "startmap": "mp_brecourt",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["uo"],
        targets=["uo"],
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
        prompt="Where would you like to install the Call of Duty: United Offensive server:",
    )
    gamemodule_common.configure_download_source(
        server,
        ask,
        url=url,
        download_name=download_name,
        default_url=CODUO_SERVER_URL,
        default_name=CODUO_SERVER_NAME,
        prompt="Direct archive URL for the Call of Duty: United Offensive server override",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def install(server):
    """Download and install the COD: United Offensive server archive."""

    if "url" not in server.data or not server.data["url"]:
        server.data["url"] = CODUO_SERVER_URL
        server.data.setdefault("download_name", CODUO_SERVER_NAME)
    install_archive(server, detect_compression(server.data["download_name"]))


def get_start_command(server):
    """Build the command used to launch a COD: United Offensive dedicated server."""

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
    """Stop COD: United Offensive using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed COD: United Offensive status is not implemented yet."""


def message(server, msg):
    """COD: United Offensive has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a COD: United Offensive server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported COD: United Offensive datastore edits."""

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
