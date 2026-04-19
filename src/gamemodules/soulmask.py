"""Soulmask dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec, build_launch_arg_values
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3017300
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The game port to use for the Soulmask server", int),
            ArgSpec("DIR", "The directory to install Soulmask in", str),
        )
    ),
    **gamemodule_common.build_update_restart_command_args(),
}
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Soulmask dedicated server to the latest version.",
    "Restart the Soulmask dedicated server.",
)
command_functions = {}
max_stop_wait = 1
setting_schema = {
    **gamemodule_common.build_unreal_setting_schema(
        positional_key="level",
        include_maxplayers=True,
        include_servername=True,
        servername_format="-SteamServerName={value}",
    ),
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Administrator password.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-adminpsw={value}",
        secret=True,
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Server password.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-PSW={value}",
        secret=True,
    ),
    "bindaddress": SettingSpec(
        canonical_key="bindaddress",
        description="Hosted IP address to bind for launch.",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-MULTIHOME={value}",
    ),
    "echoport": SettingSpec(
        canonical_key="echoport",
        description="Echo service port.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-EchoPort={value}",
    ),
    "savinginterval": SettingSpec(
        canonical_key="savinginterval",
        description="Autosave interval in seconds.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-saving={value}",
    ),
    "backupinterval": SettingSpec(
        canonical_key="backupinterval",
        description="Backup interval in seconds.",
        value_type="integer",
        apply_to=("datastore", "launch_args"),
        launch_arg_format="-backup={value}",
    ),
    "mods": SettingSpec(canonical_key="mods", description="Optional mod list."),
    **gamemodule_common.build_executable_path_setting_schema(),
}


def configure(server, ask, port=None, dir=None, *, exe_name="WSServer.sh"):
    """Collect and store configuration values for a Soulmask server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("queryport", "27015")
    server.data.setdefault("echoport", "18888")
    server.data.setdefault("servername", "AlphaGSM %s" % (server.name,))
    server.data.setdefault("level", "Level01_Main")
    server.data.setdefault("adminpassword", "alphagsm")
    server.data.setdefault("serverpassword", "")
    server.data.setdefault("maxplayers", "10")
    server.data.setdefault("bindaddress", "0.0.0.0")
    server.data.setdefault("backupinterval", "900")
    server.data.setdefault("savinginterval", "600")
    server.data.setdefault("mods", "")
    server.data.setdefault("backupfiles", ["WS/Saved"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["WS/Saved"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 8777)
    if ask:
        inp = input("Please specify the game port to use for this server: [%s] " % (port,)).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input("Where would you like to install the Soulmask server: [%s] " % (dir,)).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


def install(server):
    """Download the Soulmask server files via SteamCMD."""

    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        server.data["dir"],
        server.data["Steam_AppID"],
        server.data["Steam_anonymous_login_possible"],
        validate=False,
    )


def update(server, validate=False, restart=False):
    """Update the Soulmask server files and optionally restart the server."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    steamcmd.download(server.data["dir"], steam_app_id, steam_anonymous_login_possible, validate=validate)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def restart(server):
    """Restart the Soulmask server."""

    server.stop()
    server.start()


def get_start_command(server):
    """Build the command used to launch a Soulmask dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    dynamic_args = build_launch_arg_values(
        server.data,
        {
            "level": setting_schema["level"],
            "servername": setting_schema["servername"],
            "maxplayers": setting_schema["maxplayers"],
            "serverpassword": setting_schema["serverpassword"],
            "adminpassword": setting_schema["adminpassword"],
            "bindaddress": setting_schema["bindaddress"],
            "port": setting_schema["port"],
            "queryport": setting_schema["queryport"],
            "echoport": setting_schema["echoport"],
            "savinginterval": setting_schema["savinginterval"],
            "backupinterval": setting_schema["backupinterval"],
        },
        require_explicit_tokens=True,
        value_transform=lambda _spec, current_value: str(current_value),
    )
    command = [
        "./" + server.data["exe_name"],
        *dynamic_args[:1],
        "-server",
        "-log",
        "-forcepassthrough",
        "-UTF8Output",
        *dynamic_args[1:],
    ]
    if server.data["mods"]:
        command.append('-mod="%s"' % (server.data["mods"],))
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Soulmask using an interrupt signal."""

    screen.send_to_server(server.name, "\003")


def status(server, verbose):
    """Detailed Soulmask status is not implemented yet."""


def message(server, msg):
    """Soulmask has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Soulmask server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Soulmask datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "queryport", "echoport", "maxplayers", "backupinterval", "savinginterval"),
        resolved_str_keys=(
            "servername",
            "level",
            "adminpassword",
            "serverpassword",
            "bindaddress",
            "mods",
            "exe_name",
            "dir",
        ),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'echoport', 'protocol': 'udp'}, {'key': 'echoport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'echoport', 'protocol': 'udp'}, {'key': 'echoport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
