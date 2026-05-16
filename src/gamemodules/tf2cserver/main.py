"""Team Fortress 2 Classified-specific lifecycle and runtime helpers."""

import os

import server.runtime as runtime_module
import utils.steamcmd as steamcmd
from server import ServerError
from utils.gamemodules import common as gamemodule_common
from utils.valve_server import define_valve_server_module


steam_app_id = 3557020
base_steam_app_id = 232250
steam_anonymous_login_possible = True

MODULE = define_valve_server_module(
    game_name="Team Fortress 2 Classified",
    engine="source",
    steam_app_id=steam_app_id,
    game_dir="tf2classified",
    executable="srcds.sh",
    default_map="4koth_frigid",
    max_players=16,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    config_subdir="cfg",
    config_default="server.cfg",
    enable_map_validation=True,
)

commands = MODULE.commands
command_args = MODULE.command_args
command_descriptions = dict(MODULE.command_descriptions)
max_stop_wait = MODULE.max_stop_wait
config_sync_keys = MODULE.config_sync_keys
setting_schema = MODULE.setting_schema
sync_server_config = MODULE.sync_server_config
list_setting_values = MODULE.list_setting_values
prestart = MODULE.prestart
restart = MODULE.restart
do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
get_query_address = MODULE.get_query_address
get_info_address = MODULE.get_info_address
wake_a2s_query = MODULE.wake_a2s_query
get_hibernating_console_info = MODULE.get_hibernating_console_info


def _default_support_dir(server):
    return os.path.join(server.data["dir"], "tf")


def _ensure_support_dir(server):
    support_dir = server.data.get("supportdir") or _default_support_dir(server)
    server.data["supportdir"] = support_dir
    return support_dir


def _refresh_executable_choice(server):
    candidates = (
        server.data.get("exe_name"),
        "srcds.sh",
        "srcds_linux64",
        "srcds_run_64",
        "srcds_run",
    )
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isfile(os.path.join(server.data["dir"], candidate)):
            server.data["exe_name"] = candidate
            save = getattr(server.data, "save", None)
            if save is not None:
                save()
            return candidate
    return server.data.get("exe_name", "srcds.sh")


def _download_tf2c_stack(server, *, validate):
    support_dir = _ensure_support_dir(server)
    os.makedirs(support_dir, exist_ok=True)
    os.makedirs(server.data["dir"], exist_ok=True)
    steamcmd.download(
        support_dir,
        base_steam_app_id,
        steam_anonymous_login_possible,
        validate=validate,
    )
    steamcmd.download(
        server.data["dir"],
        steam_app_id,
        steam_anonymous_login_possible,
        validate=validate,
    )


def configure(server, ask, port=None, dir=None, *, exe_name="srcds.sh"):
    """Store TF2C defaults, including its required base TF2 support install."""

    result = MODULE.configure(server, ask, port, dir, exe_name=exe_name)
    _ensure_support_dir(server)
    save = getattr(server.data, "save", None)
    if save is not None:
        save()
    return result


def doinstall(server):
    """Download both the base TF2 server and the TF2C dedicated server."""

    _download_tf2c_stack(server, validate=False)


def install(server):
    """Install TF2C and ensure its Source config exists."""

    doinstall(server)
    _refresh_executable_choice(server)
    sync_server_config(server)
    save = getattr(server.data, "save", None)
    if save is not None:
        save()


def update(server, validate=False, restart=False):
    """Update both TF2C and its required base TF2 support files."""

    try:
        server.stop()
    except Exception:
        print("Server has probably already stopped, updating")
    _download_tf2c_stack(server, validate=validate)
    _refresh_executable_choice(server)
    sync_server_config(server)
    print("Server up to date")
    if restart:
        print("Starting the server up")
        server.start()


def get_start_command(server):
    """Build the launch command for a TF2C dedicated server."""

    exe_name = _refresh_executable_choice(server)
    exe_path = os.path.join(server.data["dir"], exe_name)
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if not exe_name.startswith("./"):
        exe_name = "./" + exe_name

    support_dir = _ensure_support_dir(server)
    command = [
        exe_name,
        "-game",
        "tf2classified",
        "-tf_path",
        support_dir,
        "-strictportbind",
        "+ip",
        "0.0.0.0",
        "-port",
        str(server.data["port"]),
    ]
    if server.data.get("clientport") is not None:
        command.extend(["+clientport", str(server.data["clientport"])])
    if server.data.get("sourcetvport") is not None:
        command.extend(["+tv_port", str(server.data["sourcetvport"])])
    command.extend(
        [
            "+map",
            str(server.data["startmap"]),
            "+servercfgfile",
            str(server.data["server_cfg"]),
            "-maxplayers",
            str(server.data["maxplayers"]),
        ]
    )
    return command, server.data["dir"]


def checkvalue(server, key, *value):
    """Validate TF2C datastore edits, including the supportdir override."""

    if len(key) == 0:
        raise ServerError("Invalid key")
    if key[0] == "supportdir":
        if len(value) == 0:
            raise ServerError("No value specified")
        return str(value[0])
    return MODULE.checkvalue(server, key, *value)


command_functions = {
    "update": update,
    "restart": restart,
}

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family="steamcmd-linux",
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
        {"key": "clientport", "protocol": "udp"},
        {"key": "sourcetvport", "protocol": "udp"},
    ),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
    family="steamcmd-linux",
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
        {"key": "clientport", "protocol": "udp"},
        {"key": "sourcetvport", "protocol": "udp"},
    ),
    stdin_open=True,
)