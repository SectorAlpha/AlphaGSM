"""ARK: Survival Ascended dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 2430930
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ARK: Survival Ascended server",
    "The directory to install ARK: Survival Ascended in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the ARK: Survival Ascended dedicated server to the latest version.",
    "Restart the ARK: Survival Ascended dedicated server.",
)
command_functions = {}
setting_schema = {
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Server admin password.",
        secret=True,
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required to join the server.",
        secret=True,
    ),
}
max_stop_wait = 1


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="ShooterGame/Binaries/Win64/ArkAscendedServer.exe",
):
    """Collect and store configuration values for an ARK: Survival Ascended server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "map": "TheIsland_WP",
            "sessionname": "AlphaGSM %s" % (server.name,),
            "adminpassword": "alphagsm",
            "serverpassword": "",
            "maxplayers": "70",
            "queryport": "27015",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ShooterGame/Saved", "ShooterGame/Saved/Config/WindowsServer"],
        targets=["ShooterGame/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=7777,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ARK: Survival Ascended server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the ARK: Survival Ascended server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the ARK: Survival Ascended server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the ARK: Survival Ascended server."


def get_start_command(server):
    """Build the command used to launch an ARK: Survival Ascended dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    map_args = (
        "%s?listen?SessionName=%s?Port=%s?QueryPort=%s?MaxPlayers=%s?ServerAdminPassword=%s"
        % (
            server.data["map"],
            server.data["sessionname"],
            server.data["port"],
            server.data["queryport"],
            server.data["maxplayers"],
            server.data["adminpassword"],
        )
    )
    if server.data["serverpassword"]:
        map_args += "?ServerPassword=%s" % (server.data["serverpassword"],)
    cmd = [server.data["exe_name"], map_args, "-server", "-log"]
    if IS_LINUX:
        cmd = proton.wrap_command(cmd, wineprefix=server.data.get("wineprefix"))
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop ARK: Survival Ascended using the standard quit command."""

    screen.send_to_server(server.name, "\nquit\n")


def status(server, verbose):
    """Detailed ARK: Survival Ascended status is not implemented yet."""


def message(server, msg):
    """ARK: Survival Ascended has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ARK: Survival Ascended server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ARK: Survival Ascended datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("map", "sessionname", "adminpassword", "serverpassword", "exe_name", "dir"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
