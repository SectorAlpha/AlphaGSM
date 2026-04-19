"""Project Zomboid dedicated server lifecycle helpers."""

import os

import screen
import utils.steamcmd as steamcmd
from server import ServerError
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec, OptSpec

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 380870
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = {
    "setup": CmdSpec(
        optionalarguments=(
            ArgSpec("PORT", "The default game port to store for this server", int),
            ArgSpec("DIR", "The directory to install Project Zomboid in", str),
        )
    ),
    "update": CmdSpec(
        options=(
            OptSpec(
                "v",
                ["validate"],
                "Validate the server files after updating",
                "validate",
                None,
                True,
            ),
            OptSpec(
                "r",
                ["restart"],
                "Restart the server after updating",
                "restart",
                None,
                True,
            ),
        )
    ),
    "restart": CmdSpec(),
}
command_descriptions = {
    "update": "Update the Project Zomboid dedicated server to the latest version.",
    "restart": "Restart the Project Zomboid dedicated server.",
}
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="start-server.sh"):
    """Collect and store configuration values for a Project Zomboid server."""

    server.data["Steam_AppID"] = steam_app_id
    server.data["Steam_anonymous_login_possible"] = steam_anonymous_login_possible
    server.data.setdefault("servername", server.name)
    server.data.setdefault("adminpassword", "alphagsm")
    server.data.setdefault("backupfiles", ["Zomboid", "Server", "start-server.sh"])
    if "backup" not in server.data:
        server.data["backup"] = {
            "profiles": {"default": {"targets": ["Zomboid", "Server"]}},
            "schedule": [("default", 0, "days")],
        }

    if port is None:
        port = server.data.get("port", 16261)
    if ask:
        inp = input(
            "Please specify the port to use for this server: [%s] " % (port,)
        ).strip()
        if inp:
            port = int(inp)
    server.data["port"] = int(port)
    # Build 41 dedicated servers expose their direct-connection listener on the
    # fixed UDP port configured in SERVERNAME.ini. Without module-managed config
    # files this remains the upstream default 16262.
    server.data.setdefault("queryport", 16262)

    if dir is None:
        dir = server.data.get("dir") or os.path.expanduser(os.path.join("~", server.name))
        if ask:
            inp = input(
                "Where would you like to install the Project Zomboid server: [%s] " % (dir,)
            ).strip()
            if inp:
                dir = inp
    server.data["dir"] = os.path.join(dir, "")
    server.data["exe_name"] = server.data.get("exe_name", exe_name)
    server.data.save()
    return (), {}


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Project Zomboid server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Project Zomboid dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "./" + server.data["exe_name"],
            "-servername",
            str(server.data["servername"]),
            "-adminpassword",
            str(server.data["adminpassword"]),
            "-port",
            str(server.data["port"]),
        ],
        server.data["dir"],
    )


def get_query_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return (runtime_module.resolve_query_host(server), int(server.data.get("queryport", 16262)), "udp")


def get_info_address(server):
    """Return the Project Zomboid direct-connection UDP listener."""

    return get_query_address(server)


def do_stop(server, j):
    """Send the standard quit command to Project Zomboid."""

    screen.send_to_server(server.name, "\nquit\n")


status = gamemodule_common.make_noop_status_hook()
status.__doc__ = "Detailed Project Zomboid status is not implemented yet."


def message(server, msg):
    """Project Zomboid has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Project Zomboid server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Project Zomboid datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("servername", "adminpassword", "exe_name", "dir"),
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
