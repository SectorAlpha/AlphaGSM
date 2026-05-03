"""Craftopia dedicated server lifecycle helpers."""

import configparser
import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1670340
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Craftopia server",
    "The directory to install Craftopia in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Craftopia dedicated server to the latest version.",
    "Restart the Craftopia dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "maxplayers", "worldname", "serverpassword", "bindaddress")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The primary game port.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        examples=("8787",),
    ),
    "map": SettingSpec(
        canonical_key="map",
        aliases=("worldname",),
        description="The selected Craftopia world name.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        storage_key="worldname",
        examples=("AlphaGSM World",),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum number of players allowed on the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        examples=("8",),
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required for joining the server.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
    "bindaddress": SettingSpec(
        canonical_key="bindaddress",
        description="IP address the server binds to.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        examples=("0.0.0.0",),
    ),
}


def _server_setting_path(server):
    return os.path.join(server.data["dir"], "ServerSetting.ini")


def _default_server_setting_path(server):
    return os.path.join(server.data["dir"], "DefaultServerSetting.ini")


def _save_dir(server):
    return os.path.join(server.data["dir"], "DedicatedServerSave")


def sync_server_config(server):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str

    default_path = _default_server_setting_path(server)
    target_path = _server_setting_path(server)
    if os.path.isfile(default_path):
        parser.read(default_path, encoding="utf-8")
    elif os.path.isfile(target_path):
        parser.read(target_path, encoding="utf-8")

    defaults = {
        "GameWorld": {
            "name": str(server.data.get("worldname", server.name)),
            "difficulty": "1",
            "gameMode": "1",
            "enemyPoolSizeRate": "1",
        },
        "Host": {
            "port": str(int(server.data.get("port", 8787))),
            "maxPlayerNumber": str(server.data.get("maxplayers", 8)),
            "usePassword": "0",
            "serverPassword": str(server.data.get("serverpassword", "00000000")),
            "bindAddress": str(server.data.get("bindaddress", "0.0.0.0")),
        },
        "Graphics": {
            "vSyncCount": "0",
            "maxFPS": "60",
            "grassBend": "0",
            "clothSimOption": "2",
        },
        "Save": {
            "autoSaveSec": "300",
            "autoSavePerHour": "1",
            "savePath": _save_dir(server) + os.sep,
        },
        "CreativeModeSetting": {
            "quickCraft": "1",
            "ageLevel": "9",
            "islandLevel": "-1",
            "noDeath": "1",
            "noDamage": "1",
            "noHunger": "1",
            "infinitStamina": "1",
            "forceDayTime": "-1",
            "buildingIgnoreDamage": "0",
            "noBuild": "0",
        },
        "CreativeModePlStatus": {
            "Level": "0",
            "Health": "0",
            "Mana": "0",
            "Stamina": "0",
            "Money": "1000",
            "SkillPoint": "0",
            "EnchantPoint": "0",
        },
    }

    for section, values in defaults.items():
        if not parser.has_section(section):
            parser.add_section(section)
        for key, value in values.items():
            parser.set(section, key, value)

    os.makedirs(_save_dir(server), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as handle:
        parser.write(handle, space_around_delimiters=False)


def configure(server, ask, port=None, dir=None, *, exe_name="Craftopia.x86_64"):
    """Collect and store configuration values for a Craftopia server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": 8787,
            "maxplayers": 8,
            "worldname": server.name,
            "serverpassword": "00000000",
            "bindaddress": "0.0.0.0",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["DedicatedServerSave", "ServerSetting.ini"],
        targets=["DedicatedServerSave", "ServerSetting.ini"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=8787,
        prompt="Please specify the game port to use for this server:",
    )
    server.data["queryport"] = int(server.data.get("queryport", server.data["port"]))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Craftopia server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _finalize_install_layout(server):
    """Restore executable bits and seed the generated Craftopia config."""

    sync_server_config(server)
    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if os.path.isfile(exe_path):
        os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    server.data.save()


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the Craftopia server files via SteamCMD."""

    _base_install(server)
    _finalize_install_layout(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Craftopia server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Craftopia server."


def get_query_address(server):
    """Return the Craftopia UDP game endpoint used for health checks."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the Craftopia UDP endpoint used for info output."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Craftopia dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    sync_server_config(server)
    return (
        [
            "./" + server.data["exe_name"],
            "-batchmode",
            "-nographics",
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop Craftopia using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Craftopia status is not implemented yet."""


def message(server, msg):
    """Craftopia has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Craftopia server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Craftopia datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("map", "serverpassword", "bindaddress"),
        raw_int_keys=("port", "queryport", "maxplayers"),
        raw_str_keys=("worldname", "exe_name", "dir", "serverpassword", "bindaddress"),
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
