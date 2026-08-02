"""Saleblazers dedicated server lifecycle helpers."""

import json
import os
import shutil

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from server.settable_keys import SettingSpec

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 3099600
steam_anonymous_login_possible = True
DEFAULT_PORT = 27015
STATUS_PORT_OFFSET = 1
config_sync_keys = ("port", "maxplayers", "servername", "serverpassword")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        description="The primary game port for the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        examples=("27015",),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        description="Maximum number of players allowed on the server.",
        value_type="integer",
        apply_to=("datastore", "native_config"),
        examples=("8",),
    ),
    "servername": SettingSpec(
        canonical_key="servername",
        description="The public lobby name for the dedicated server.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        examples=("AlphaGSM Test",),
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Optional password required to join the server.",
        value_type="string",
        apply_to=("datastore", "native_config"),
        secret=True,
    ),
}

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Saleblazers server",
    "The directory to install Saleblazers in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Saleblazers dedicated server to the latest version.",
    "Restart the Saleblazers dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Default/Saleblazers.exe"):
    """Collect and store configuration values for a Saleblazers server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "8",
            "servername": server.name,
            "serverpassword": "",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saleblazers_Data", "ServerSave", "DedicatedServerConfig.json"],
        targets=["Saleblazers_Data", "ServerSave", "DedicatedServerConfig.json"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=DEFAULT_PORT,
        prompt="Please specify the game port to use for this server:",
    )
    _sync_runtime_ports(server)
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Saleblazers server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _config_path(server):
    """Return the managed Saleblazers dedicated config path."""

    return os.path.join(server.data["dir"], "DedicatedServerConfig.json")


def _status_port(server):
    """Return the observed Saleblazers UDP status port."""

    return int(server.data.get("port", DEFAULT_PORT)) + STATUS_PORT_OFFSET


def _sync_runtime_ports(server):
    """Keep the derived Saleblazers status port aligned with the game port."""

    server.data["queryport"] = str(_status_port(server))


def _config_template_path():
    """Return the packaged Saleblazers config template path."""

    return os.path.join(os.path.dirname(__file__), "dedicated_server_config_template.json")


def _load_config_payload(server):
    """Load the managed Saleblazers config payload, seeding from the template."""

    config_path = _config_path(server)
    source_path = config_path if os.path.isfile(config_path) else _config_template_path()
    with open(source_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _set_serialized_option(payload, key, value):
    """Set or add a serialized lobby option inside the managed config payload."""

    options = payload["LobbyConfig"]["SerializedOptions"]["Options"]
    for item in options:
        if item.get("Key") == key:
            item["Value"] = value
            return
    options.append({"Key": key, "Value": value})


def sync_server_config(server):
    """Keep the managed Saleblazers config aligned with AlphaGSM data."""

    payload = _load_config_payload(server)
    payload.setdefault("LoginConfig", {})["HostingPort"] = int(server.data.get("port", 27015))
    lobby_config = payload.setdefault("LobbyConfig", {})
    lobby_config.setdefault("HostOptions", {})
    lobby_config.setdefault("SerializedOptions", {}).setdefault("Options", [])
    lobby_config.setdefault("AutoSaveIntervalSeconds", 600)
    lobby_config.setdefault("bAdvertiseServer", True)
    server_name = str(server.data.get("servername", server.name))
    _set_serialized_option(payload, "Lobby_Name", server_name)
    _set_serialized_option(payload, "Lobby_HostName", server_name)
    _set_serialized_option(payload, "Lobby_Password", str(server.data.get("serverpassword", "")))
    _set_serialized_option(payload, "Lobby_Capacity", str(server.data.get("maxplayers", "8")))
    _set_serialized_option(payload, "Lobby_DedicatedServer", "True")

    config_path = _config_path(server)
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
install.__doc__ = "Download the Saleblazers server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)

restart = gamemodule_common.make_restart_hook()


def _wrap_linux_command(command, wineprefix=None):
    """Wrap the Windows server command for headless Linux hosts."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
    )
    wrapped = proton.prepend_env_assignments(
        wrapped,
        LIBGL_ALWAYS_SOFTWARE="1",
    )
    if shutil.which("xvfb-run") is None:
        return wrapped
    wrapped = proton.prepend_env_assignments(
        wrapped,
        SDL_VIDEODRIVER="x11",
        SDL_AUDIODRIVER="dummy",
    )
    wrapped = [
        arg
        for arg in wrapped
        if not (
            arg.startswith("DISPLAY=")
            or arg.startswith("WINEDLLOVERRIDES=")
        )
    ]
    return ["xvfb-run", "-a", *wrapped]


def get_query_address(server):
    """Return the Saleblazers generic UDP status endpoint."""

    return (runtime_module.resolve_query_host(server), _status_port(server), "udp")


def get_info_address(server):
    """Return the Saleblazers generic UDP info endpoint."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch a Saleblazers server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    working_dir = os.path.dirname(exe_path) or server.data["dir"]
    config_path = os.path.relpath(_config_path(server), working_dir)
    log_path = os.path.relpath(
        os.path.join(server.data["dir"], "server.log"),
        working_dir,
    )
    cmd = [
        os.path.basename(server.data["exe_name"]),
        "-headless",
        "-config",
        config_path,
        "-batchmode",
        "-nographics",
        "-logFile",
        log_path,
    ]
    if IS_LINUX:
        # Unity's explicit headless flags push this build onto a NullGfx path
        # that never reaches the dedicated console on Linux/Wine. Keep the
        # Xvfb-backed windowed server path and only retain batch logging.
        cmd = [
            os.path.basename(server.data["exe_name"]),
            "-config",
            config_path,
            "-batchmode",
            "-logFile",
            log_path,
        ]
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, working_dir


def prestart(server):
    """Refresh the dedicated config before each launch."""

    _sync_runtime_ports(server)
    sync_server_config(server)


def do_stop(server, j):
    """Stop Saleblazers using an interrupt signal."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed Saleblazers status is not implemented yet."


def message(server, msg):
    """Saleblazers has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Saleblazers server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Saleblazers datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("exe_name", "dir", "servername", "serverpassword"),
    )

_shared_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)


def get_runtime_requirements(server):
    """Expose the game port plus the observed helper surface."""

    _sync_runtime_ports(server)
    return _shared_runtime_requirements(server)


_shared_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=(
        {"key": "queryport", "protocol": "udp"},
        {"key": "queryport", "protocol": "tcp"},
        {"key": "port", "protocol": "udp"},
        {"key": "port", "protocol": "tcp"},
    ),
)


def get_container_spec(server):
    """Expose the container contract with the derived helper port included."""

    _sync_runtime_ports(server)
    return _shared_container_spec(server)
