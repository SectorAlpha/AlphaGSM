"""7 Days to Die dedicated server lifecycle helpers."""

import os
import re

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_native_config_values
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 294420
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the 7 Days to Die server",
    "The directory to install 7 Days to Die in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the 7 Days to Die dedicated server to the latest version.",
    "Restart the 7 Days to Die dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "servername", "maxplayers", "serverpassword")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The game port to use for this server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerPort",
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The advertised server name.",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerName",
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum allowed players.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerMaxPlayerCount",
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Optional join password.",
        apply_to=("datastore", "native_config"),
        native_config_key="ServerPassword",
        secret=True,
    ),
}


def configure(server, ask, port=None, dir=None, *, exe_name="startserver.sh"):
    """Collect and store configuration values for a 7 Days to Die server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(server, {"configfile": "serverconfig.xml"})
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saves", "serverconfig.xml", "startserver.sh"],
        targets=["Saves", "serverconfig.xml"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=26900,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the 7 Days to Die server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def sync_server_config(server):
    """Update managed serverconfig.xml entries to match server.data."""

    configfile = server.data.get("configfile", "serverconfig.xml")
    config_path = os.path.join(server.data["dir"], configfile)
    if not os.path.isfile(config_path):
        return
    replacements = build_native_config_values(
        server.data,
        setting_schema,
        defaults={
            "port": 26900,
            "servername": "AlphaGSM %s" % (server.name,),
            "maxplayers": 8,
            "serverpassword": "",
        },
        require_explicit_key=True,
        value_transform=lambda spec, current_value: (
            str(int(current_value)) if spec.value_type == "integer" else str(current_value)
        ),
    )
    if not replacements:
        return
    with open(config_path, encoding="utf-8") as fh:
        content = fh.read()
    new_content = content
    for xml_key, replacement_value in replacements.items():
        new_content = re.sub(
            rf'(<property\s+name="{re.escape(xml_key)}"\s+value=")[^"]*(")',
            r'\g<1>' + replacement_value + r'\2',
            new_content,
        )
    if new_content != content:
        with open(config_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


def install(server):
    """Download the 7 Days to Die server files via SteamCMD."""

    _base_install(server)
    sync_server_config(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the 7 Days to Die server files and optionally restart the server."


def prestart(server, *args, **kwargs):
    """Refresh serverconfig.xml from the current datastore before launch."""

    sync_server_config(server)


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the 7 Days to Die server."


def get_start_command(server):
    """Build the command used to launch a 7 Days to Die dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        ["./" + server.data["exe_name"], "-configfile=%s" % (server.data["configfile"],)],
        server.data["dir"],
    )


def do_stop(server, j):
    """Send the standard shutdown command to 7 Days to Die."""

    screen.send_to_server(server.name, "\nshutdown\n")


def status(server, verbose):
    """Detailed 7 Days to Die status is not implemented yet."""


def message(server, msg):
    """7 Days to Die has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a 7 Days to Die server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported 7 Days to Die datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("configfile", "exe_name", "dir", "servername", "serverpassword"),
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
