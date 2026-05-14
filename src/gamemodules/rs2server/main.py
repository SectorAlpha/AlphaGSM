"""Rising Storm 2: Vietnam dedicated server lifecycle helpers."""

import os

import screen
import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values, build_native_config_values

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 418480
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Rising Storm 2 server",
    "The directory to install Rising Storm 2 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Rising Storm 2: Vietnam dedicated server to the latest version.",
    "Restart the Rising Storm 2: Vietnam dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("servername",)
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(),
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("hostname", "server_name", "name"),
        description="The advertised server name.",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerName",
    ),
    "configfile": SettingSpec(canonical_key="configfile", description="Config file path for the server."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def _config_path(server):
    configfile = server.data.get("configfile", "ROGame/Config/PCServer-ROGame.ini")
    return os.path.join(server.data["dir"], configfile)


def _rewrite_ini_setting(path, section_name, key_name, value):
    rendered_value = str(value)
    if os.path.isfile(path):
        lines = open(path, "r", encoding="utf-8").read().splitlines(True)
    else:
        lines = []

    section_header = "[%s]" % (section_name,)
    key_prefix = key_name + "="
    current_section = None
    section_start = None
    insert_index = None

    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current_section == section_name and insert_index is None:
                insert_index = index
            current_section = stripped[1:-1]
            if current_section == section_name:
                section_start = index
            continue
        if current_section != section_name:
            continue
        if stripped.startswith(key_prefix):
            lines[index] = "%s=%s\n" % (key_name, rendered_value)
            with open(path, "w", encoding="utf-8") as handle:
                handle.writelines(lines)
            return

    if section_start is not None:
        if insert_index is None:
            insert_index = len(lines)
        lines.insert(insert_index, "%s=%s\n" % (key_name, rendered_value))
    else:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.extend([
            "%s\n" % (section_header,),
            "%s=%s\n" % (key_name, rendered_value),
        ])

    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)


def sync_server_config(server):
    """Rewrite managed Rising Storm 2 config entries from datastore values."""

    config_path = _config_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    config_values = build_native_config_values(
        server.data,
        setting_schema,
        defaults={"servername": "AlphaGSM %s" % (server.name,)},
        require_explicit_key=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    if "ServerName" in config_values:
        _rewrite_ini_setting(
            config_path,
            "/Script/Engine.GameReplicationInfo",
            "ServerName",
            config_values["ServerName"],
        )


def configure(server, ask, port=None, dir=None, *, exe_name="Binaries/Win64/VNGame.exe"):
    """Collect and store configuration values for a Rising Storm 2 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27015",
            "configfile": "ROGame/Config/PCServer-ROGame.ini",
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ROGame/Config", "ROGame/Saved"],
        targets=["ROGame/Config", "ROGame/Saved"],
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
        prompt="Where would you like to install the Rising Storm 2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
install.__doc__ = "Download the Rising Storm 2 server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
update.__doc__ = "Update the Rising Storm 2 server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Rising Storm 2 server."


def get_start_command(server):
    """Build the command used to launch a Rising Storm 2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        setting_schema,
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    cmd = [
            server.data["exe_name"],
            "VNTE-CuChi?maxplayers=64",
            *dynamic_args,
            "-ConfigSubDir=PCServer",
            "-log",
        ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop Rising Storm 2 using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Rising Storm 2 status is not implemented yet."""


def message(server, msg):
    """Rising Storm 2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Rising Storm 2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Rising Storm 2 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport"),
        resolved_str_keys=("servername", "configfile", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)
