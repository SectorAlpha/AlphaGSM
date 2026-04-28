"""Call of Duty: Black Ops III dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 545990
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Black Ops III server",
    "The directory to install Black Ops III in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Black Ops III dedicated server to the latest version.",
    "Restart the Black Ops III dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port for the server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("-port",),
        examples=("28960",),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="The maximum number of players.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_tokens=("+set", "sv_maxclients"),
        examples=("18",),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="UnrankedServer/BlackOps3_UnrankedDedicatedServer.exe"):
    """Collect and store configuration values for a Black Ops III server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"maxplayers": "18"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["players", "zone", "mods"],
        targets=["players", "zone", "mods"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=28960,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Black Ops III server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Black Ops III server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Black Ops III dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    # The bat file (Launch_Server.bat) uses 'BlackOps3_UnrankedDedicatedServer.exe'
    # as a bare name, which fails when cmd.exe runs from the parent install dir.
    # We run the exe directly from its own directory so DLL loading succeeds.
    # Use the basename only (no path prefix) because cwd is already the exe dir.
    cmd = [
        "BlackOps3_UnrankedDedicatedServer.exe",
        "+set", "sv_playlist", "1",
        "+set", "fs_game", "usermaps",
        "+set", "logfile", "2",
        *dynamic_args,
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
    unranked_dir = os.path.join(server.data["dir"], "UnrankedServer")
    return cmd, unranked_dir


def get_query_address(server):
    """Return A2S query address for Black Ops III (IW engine uses game port)."""
    return "127.0.0.1", int(server.data["port"]), "a2s"


def get_info_address(server):
    """Return A2S info address for Black Ops III (IW engine uses game port)."""
    return "127.0.0.1", int(server.data["port"]), "a2s"


def do_stop(server, j):
    """Stop Black Ops III by interrupting the foreground server process."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Black Ops III status is not implemented yet."


def message(server, msg):
    """Black Ops III has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Black Ops III server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Black Ops III datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
