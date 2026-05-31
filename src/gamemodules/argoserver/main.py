"""Argo dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 563930
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Argo in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Argo dedicated server to the latest version.",
    "Restart the Argo dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("servername",)
setting_schema = {
    "servername": SettingSpec(
        canonical_key="servername",
        aliases=("hostname",),
        description="The public hostname written to server.cfg.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        native_config_key="hostname",
        examples=("AlphaGSM Server",),
    )
}


def sync_server_config(server):
    """Write managed server.cfg values from datastore settings."""

    if "dir" not in server.data:
        return
    configfile = server.data.get("configfile", "server.cfg")
    servername = server.data.get("servername", "AlphaGSM %s" % (server.name,))
    config_path = os.path.join(server.data["dir"], configfile)
    config_dir = os.path.dirname(config_path)
    if config_dir:
        os.makedirs(config_dir, exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write('hostname = "%s";\n' % (servername.replace('"', '\\"'),))


def configure(server, ask, port=None, dir=None, *, exe_name="argoserver"):
    """Collect and store configuration values for an Argo server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "configfile": "server.cfg",
            "profilesdir": "profiles",
            "servername": "AlphaGSM %s" % (server.name,),
            "world": "empty",
            "mod": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["profiles", "server.cfg"],
        targets=["profiles", "server.cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=2302,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Argo server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the Argo server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the Argo server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Argo server."


def get_start_command(server):
    """Build the command used to launch an Argo dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        "./" + server.data["exe_name"],
        "-config=%s" % (server.data["configfile"],),
        "-port=%s" % (server.data["port"],),
        "-profiles=%s" % (server.data["profilesdir"],),
        "-name=%s" % (server.name,),
        "-world=%s" % (server.data["world"],),
        "-autoinit",
    ]
    if server.data["mod"]:
        command.append("-mod=%s" % (server.data["mod"],))
    return (command, server.data["dir"])


def do_stop(server, j):
    """Stop Argo by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Argo status is not implemented yet."""


def message(server, msg):
    """Argo has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an Argo server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Argo datastore edits."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "backup":
        return backup_utils.checkdatavalue(server.data["backup"], key, *value)
    if len(value) == 0:
        raise ServerError("No value specified")
    if key[0] == "port":
        return int(value[0])
    if key[0] in ("configfile", "profilesdir", "servername", "world", "mod", "exe_name", "dir"):
        return str(value[0])
    raise ServerError("Unsupported key")

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
