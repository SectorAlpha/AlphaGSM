"""V Rising dedicated server lifecycle helpers."""

import json
import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1829350
steam_anonymous_login_possible = True
config_sync_keys = ("port", "queryport", "maxplayers", "servername")

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install V Rising in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the V Rising dedicated server to the latest version.",
    "Restart the V Rising dedicated server.",
)
command_functions = {}
max_stop_wait = 1


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


def configure(server, ask, port=None, dir=None, *, exe_name="VRisingServer.exe"):
    """Collect and store configuration values for a V Rising server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "9877",
            "maxplayers": "40",
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["save-data", "Settings"],
        targets=["save-data", "Settings"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=9876,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the V Rising server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _settings_dir(server):
    return os.path.join(server.data["dir"], "Settings")


def _server_host_settings_path(server):
    return os.path.join(_settings_dir(server), "ServerHostSettings.json")


def _server_host_template_path():
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "..",
            "docs",
            "server-templates",
            "vrserver",
            "ServerHostSettings.json",
        )
    )


def _load_server_host_settings(server):
    config_path = _server_host_settings_path(server)
    source_path = config_path if os.path.isfile(config_path) else _server_host_template_path()
    with open(source_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def sync_server_config(server):
    """Keep ServerHostSettings.json aligned with AlphaGSM data."""

    server_dir = server.data.get("dir")
    if not server_dir:
        return
    payload = _load_server_host_settings(server)
    payload["Name"] = str(server.data.get("servername") or ("AlphaGSM %s" % (server.name,)))
    payload["Port"] = int(server.data.get("port", 9876))
    payload["QueryPort"] = int(server.data.get("queryport", 9877))
    payload["MaxConnectedUsers"] = int(server.data.get("maxplayers", 40))

    config_path = _server_host_settings_path(server)
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the V Rising server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the V Rising server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the V Rising server."


def prestart(server):
    """Refresh V Rising JSON settings before launch."""

    sync_server_config(server)


def get_query_address(server):
    """Return the validated runtime query surface for V Rising."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "udp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for V Rising."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a V Rising dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        server.data["exe_name"],
        "-persistentDataPath",
        os.path.join(server.data["dir"], "save-data"),
        "-serverPort",
        str(server.data["port"]),
        "-queryPort",
        str(server.data["queryport"]),
    ]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop the V Rising server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed V Rising status is not implemented yet."""


def message(server, msg):
    """V Rising has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a V Rising server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported V Rising datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("servername", "exe_name", "dir"),
    )


get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_env=_container_runtime_env,
)
