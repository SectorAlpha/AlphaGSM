"""BattleBit Remastered dedicated server lifecycle helpers."""

import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec
from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 689410
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the BattleBit server",
    "The directory to install BattleBit in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the BattleBit dedicated server to the latest version.",
    "Restart the BattleBit dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port for the BattleBit community server.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-Port={value}",
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="The maximum number of players.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-MaxPlayers={value}",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("name",),
        description="The advertised BattleBit community server name.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-Name={value}",
    ),
    "apiendpoint": SettingSpec(
        canonical_key="apiendpoint",
        aliases=("api_endpoint",),
        description="BattleBit community server API endpoint in host:port form.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-ApiEndPoint={value}",
    ),
    "apitoken": SettingSpec(
        canonical_key="apitoken",
        aliases=("api_token",),
        description="Optional BattleBit community server API token.",
        secret=True,
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-ApiToken={value}",
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _container_runtime_env(_server):
    """Return Docker runtime env for the shared wine-proton entrypoint."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 1024x768x24 -nolisten tcp",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }


def configure(server, ask, port=None, dir=None, *, exe_name="BattleBit.exe"):
    """Collect and store configuration values for a BattleBit server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": "127",
            "apiendpoint": "",
            "apitoken": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["UserData", "BattleBit_Data"],
        targets=["UserData", "BattleBit_Data"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=29992,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the BattleBit server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def get_provider_requirements(server):
    """Declare the provider-managed prerequisites for BattleBit community servers."""

    return [
        {
            "provider": "battlebit",
            "kind": "provisioning",
            "keys": ("apiendpoint",),
            "required_for": ("start",),
            "support_category": "provider-provisioning",
            "summary": "BattleBit community-server API provisioning and a reachable apiendpoint",
            "actions": (
                "Set apiendpoint to the BattleBit community server API host:port before starting",
                "If your API requires verification, also set apitoken before starting",
                "Ensure the host is approved for BattleBit community-server hosting per the official agreement and TOS",
            ),
            "docs_slug": "battlebitserver",
        }
    ]


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the BattleBit server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the BattleBit server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the BattleBit server."


def get_start_command(server):
    """Build the command used to launch a BattleBit dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    gamemodule_common.validate_provider_requirements(
        "battlebitserver",
        server,
        phase="start",
        requirements=get_provider_requirements(server),
    )
    cmd = [
        server.data["exe_name"],
        "-batchmode",
        "-nographics",
        "-Name=%s" % (server.data.get("servername") or ("AlphaGSM %s" % (server.name,))),
        "-Port=%s" % (server.data["port"],),
        "-MaxPlayers=%s" % (server.data["maxplayers"],),
        "-AntiCheat=EAC",
        "-ApiEndPoint=%s" % (server.data["apiendpoint"],),
    ]
    if str(server.data.get("apitoken", "")).strip():
        cmd.append("-ApiToken=%s" % (server.data["apitoken"],))
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return (cmd, server.data["dir"])


def do_stop(server, j):
    """Stop BattleBit by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed BattleBit status is not implemented yet."""


def message(server, msg):
    """BattleBit has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a BattleBit server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported BattleBit datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("servername", "apiendpoint", "apitoken", "exe_name", "dir"),
        backup_module=backup_utils,
    )


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)
