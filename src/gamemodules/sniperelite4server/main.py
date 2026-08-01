"""Sniper Elite 4 dedicated server lifecycle helpers."""

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

steam_app_id = 568880
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the Sniper Elite 4 server",
    "The directory to install Sniper Elite 4 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Sniper Elite 4 dedicated server to the latest version.",
    "Restart the Sniper Elite 4 dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "maxplayers")
setting_schema = {
    "port": SettingSpec(
        canonical_key="port",
        value_type="integer",
        description="The game port for the server.",
        apply_to=("datastore", "config"),
    ),
    "maxplayers": SettingSpec(
        canonical_key="maxplayers",
        value_type="integer",
        description="The maximum number of players.",
        apply_to=("datastore", "config"),
    ),
    **gamemodule_common.build_executable_path_setting_schema(),
}

DEFAULT_CFG_PATH = "default.cfg"
EXAMPLE_DEFAULT_CFG_PATH = os.path.join("Docs", "ExampleConfigs", "Example1.cfg")
DEFAULT_MAP_DIRECTIVE = "MapRotation.AddMap VILLAGE DM"
MANAGED_CONFIG_DIRECTIVES = (
    "Server.Name",
    "Server.AuthPort",
    "Server.GamePort",
    "Server.UpdatePort",
    "Server.LobbyPort",
    "Settings.MaxPlayers",
    "Server.Host",
)
port_claim_definitions = (
    {"key": "port", "protocol": "udp"},
    {"key": "port", "offset": 1, "protocol": "udp"},
    {"key": "port", "offset": 2, "protocol": "udp"},
    {"key": "port", "offset": 3, "protocol": "tcp"},
)


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


def _wrap_linux_command(command, wineprefix=None):
    """Wrap Sniper Elite 4 for headless Linux process launches."""

    wrapped = proton.wrap_command(
        command,
        wineprefix=wineprefix,
        prefer_proton=True,
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
    return [
        "xvfb-run",
        "-a",
        "--server-args=-screen 0 1024x768x24 -nolisten tcp",
        *wrapped,
    ]


def configure(server, ask, port=None, dir=None, *, exe_name="bin/SniperElite4_Dedicated.exe"):
    """Collect and store configuration values for a Sniper Elite 4 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "maxplayers": "12",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["config", "save"],
        targets=["config", "save"],
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
        prompt="Where would you like to install the Sniper Elite 4 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _ensure_default_cfg(server):
    """Stage a default.cfg in the install root when the depot ships only examples."""

    default_cfg_path = os.path.join(server.data["dir"], DEFAULT_CFG_PATH)
    if os.path.isfile(default_cfg_path):
        return

    example_cfg_path = os.path.join(server.data["dir"], EXAMPLE_DEFAULT_CFG_PATH)
    if os.path.isfile(example_cfg_path):
        shutil.copyfile(example_cfg_path, default_cfg_path)
        return

    with open(default_cfg_path, "w", encoding="utf-8") as cfg_file:
        cfg_file.write("// AlphaGSM generated default.cfg\n")


def sync_server_config(server):
    """Write AlphaGSM-owned settings into Sniper Elite 4's default.cfg."""

    _ensure_default_cfg(server)
    default_cfg_path = os.path.join(server.data["dir"], DEFAULT_CFG_PATH)
    with open(default_cfg_path, "r", encoding="utf-8") as cfg_file:
        lines = cfg_file.read().splitlines()

    preserved_lines = []
    has_map_rotation = False
    for line in lines:
        directive = line.strip().split(None, 1)[0] if line.strip() else ""
        if directive == "MapRotation.AddMap":
            has_map_rotation = True
        if directive in MANAGED_CONFIG_DIRECTIVES:
            continue
        preserved_lines.append(line)

    port = int(server.data.get("port", 7777))
    maxplayers = int(server.data.get("maxplayers", 12))
    if not has_map_rotation:
        preserved_lines.append(DEFAULT_MAP_DIRECTIVE)
    managed_lines = [
        "Server.Name {}".format(server.name),
        "Server.GamePort {}".format(port),
        "Server.AuthPort {}".format(port + 1),
        "Server.UpdatePort {}".format(port + 2),
        "Server.LobbyPort {}".format(port + 3),
        "Settings.MaxPlayers {}".format(maxplayers),
        "Server.Host",
    ]
    while preserved_lines and not preserved_lines[-1].strip():
        preserved_lines.pop()
    output_lines = preserved_lines + [""] + managed_lines
    with open(default_cfg_path, "w", encoding="utf-8") as cfg_file:
        cfg_file.write("\n".join(output_lines).lstrip("\n") + "\n")


_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)
_base_install.__doc__ = "Download the Sniper Elite 4 server files via SteamCMD."

_base_update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
    download_kwargs={"force_windows": IS_LINUX},
)


def install(server, *args, **kwargs):
    """Download the Sniper Elite 4 server files and stage default.cfg."""

    result = _base_install(server, *args, **kwargs)
    _ensure_default_cfg(server)
    return result


def update(server, *args, **kwargs):
    """Update the Sniper Elite 4 server files and refresh default.cfg."""

    result = _base_update(server, *args, **kwargs)
    _ensure_default_cfg(server)
    return result

restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    """Build the command used to launch a Sniper Elite 4 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [
        server.data["exe_name"],
        "exec",
        DEFAULT_CFG_PATH,
    ]
    if IS_LINUX:
        cmd = _wrap_linux_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
        )
    return cmd, server.data["dir"]


def prestart(server):
    """Ensure the install-root default.cfg exists before launch."""

    sync_server_config(server)


def do_stop(server, j):
    """Stop Sniper Elite 4 by interrupting the foreground server process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Sniper Elite 4 status is not implemented yet."""


def message(server, msg):
    """Sniper Elite 4 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Sniper Elite 4 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_address(server):
    """Return Sniper Elite 4's configured UDP game-port health surface."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the same UDP health surface used by the info command."""

    return get_query_address(server)


def checkvalue(server, key, *value):
    """Validate supported Sniper Elite 4 datastore edits."""

    return gamemodule_common.handle_setting_schema_checkvalue(
        server,
        key,
        *value,
        setting_schema=setting_schema,
        resolved_int_keys=("port", "maxplayers"),
        resolved_str_keys=("exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=port_claim_definitions,
    prefer_proton=True,
    extra_env=_container_runtime_env,
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=port_claim_definitions,
    prefer_proton=True,
    extra_env=_container_runtime_env,
)
