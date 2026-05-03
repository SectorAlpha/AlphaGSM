"""Smalland dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 808040
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Smalland server",
    "The directory to install Smalland in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Smalland dedicated server to the latest version.",
    "Restart the Smalland dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="Primary gameplay port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-port={value}",
    ),
    "servername": SettingSpec(canonical_key="servername", description="Configured public server name."),
    "worldname": SettingSpec(canonical_key="worldname", description="Configured persistent world name."),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Optional join password.",
        secret=True,
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _build_launch_args(server):
    """Build the Smalland world and runtime arguments passed to the UE server."""

    world_arg = gamemodule_common.build_unreal_travel_arg(
        "/Game/Maps/WorldGame/WorldGame_Smalland",
        options=(
            ("SERVERNAME", '"{}"'.format(server.data["servername"])),
            ("WORLDNAME", '"{}"'.format(server.data["worldname"])),
            ("lengthofdayseconds", "1800"),
            ("lengthofseasonseconds", "10800"),
            ("creaturehealthmodifier", "100"),
            ("creaturedamagemodifier", "100"),
            ("creaturerespawnratemodifier", "100"),
            ("resourcerespawnratemodifier", "100"),
            ("creaturespawnchancemodifier", "100"),
            ("craftingtimemodifier", "100"),
            ("craftingfuelmodifier", "100"),
            ("stormfrequencymodifier", "100"),
            ("nourishmentlossmodifier", "100"),
            ("falldamagemodifier", "100"),
            ("SESSIONPLATFORM", "pc"),
        ),
        optional_options=(
            (
                "PASSWORD",
                '"{}"'.format(server.data["serverpassword"])
                if server.data.get("serverpassword")
                else "",
            ),
        ),
        flags=("CROSSPLAY",),
    )
    launch_args = build_launch_arg_values(
        server.data,
        {"port": setting_schema["port"]},
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    return [
        world_arg,
        "-ini:Engine:[EpicOnlineServices]:DeploymentId=50f2b148496e4cbbbdeefbecc2ccd6a3",
        "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientId=xyza78918KT08TkA6emolUay8yhvAAy2",
        "-ini:Engine:[EpicOnlineServices]:DedicatedServerClientSecret=aN2GtVw7aHb6hx66HwohNM+qktFaO3vtrLSbGdTzZWk",
        *launch_args,
        "-NOSTEAM",
        "-log",
    ]


def configure(server, ask, port=None, dir=None, *, exe_name="SMALLANDServer.sh"):
    """Collect and store configuration values for a Smalland server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "worldname": "World",
            "servername": "AlphaGSM %s" % (server.name,),
            "serverpassword": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saved", "Config"],
        targets=["Saved", "Config"],
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
        prompt="Where would you like to install the Smalland server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _mark_launch_scripts_executable(server):
    """Restore executable bits on shipped launcher scripts when present."""

    for script_name in ("start-server.sh", "SMALLANDServer.sh"):
        script_path = os.path.join(server.data["dir"], script_name)
        if os.path.isfile(script_path):
            os.chmod(script_path, os.stat(script_path).st_mode | 0o111)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_mark_launch_scripts_executable,
)
install.__doc__ = "Download the Smalland server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    post_download_hook=_mark_launch_scripts_executable,
)
update.__doc__ = "Update the Smalland server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Smalland server."


def get_start_command(server):
    """Build the command used to launch a Smalland dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], *_build_launch_args(server)],
        server.data["dir"],
    )


def get_query_address(server):
    """Smalland exposes a silent UDP listener on the main game port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Smalland's info surface is the same UDP listener as its query surface."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Smalland using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Smalland status is not implemented yet."""


def message(server, msg):
    """Smalland has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Smalland server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Smalland datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port",),
        resolved_str_keys=("servername", "worldname", "serverpassword", "exe_name", "dir"),
        raw_int_keys=("queryport",),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
)
