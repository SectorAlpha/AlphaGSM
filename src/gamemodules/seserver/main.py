"""Space Engineers dedicated server lifecycle helpers."""

import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError

from utils.platform_info import IS_LINUX
import server.runtime as runtime_module
from server.modsupport.native_workshop import build_native_workshop_support
from .workshop import WORKSHOP_APP_ID, apply_workshop
from .configuration import sync_server_config
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 298740
steam_anonymous_login_possible = True
workshop_app_id = WORKSHOP_APP_ID
MOD_SUPPORT = build_native_workshop_support(
    game_label="Space Engineers", workshop_app_id=workshop_app_id, apply_callback=apply_workshop,
)
CONTAINER_WORKING_DIR = f"{proton.CONTAINER_SERVER_DIR}/DedicatedServer64"
DEFAULT_EXECUTABLES = (
    "DedicatedServer64/SpaceEngineersDedicated.exe",
    "DedicatedServer/SpaceEngineersDedicated.exe",
)

commands = ("update", "restart") + MOD_SUPPORT.commands
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Space Engineers in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Space Engineers dedicated server to the latest version.",
    "Restart the Space Engineers dedicated server.",
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions = dict(MOD_SUPPORT.command_functions)
max_stop_wait = 1
config_sync_keys = ("port", "servername", "maxplayers")


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


def _data_path(server):
    """Return the dedicated-server data path expected by the binary."""

    server_dir = os.path.abspath(server.data["dir"])
    if IS_LINUX:
        normalized = server_dir.replace("\\", "/")
        return "Z:" + normalized.replace("/", "\\")
    return server_dir


def _resolve_executable_name(server):
    """Return the real dedicated executable from the installed payload."""

    configured = server.data.get("exe_name")
    candidates = []
    if configured:
        candidates.append(configured)
    candidates.extend(name for name in DEFAULT_EXECUTABLES if name not in candidates)

    for candidate in candidates:
        if os.path.isfile(os.path.join(server.data["dir"], candidate)):
            return candidate
    raise ServerError("Executable file not found")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="DedicatedServer64/SpaceEngineersDedicated.exe",
):
    """Collect and store configuration values for a Space Engineers server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Saves", "Storage", "SpaceEngineers-Dedicated.cfg", "SpaceEngineers.cfg"],
        targets=["Saves", "Storage", "SpaceEngineers-Dedicated.cfg", "SpaceEngineers.cfg"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27016,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Space Engineers server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    MOD_SUPPORT.ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


def apply_automatic_mods(server):
    """Respect the lifecycle autoapply switch, including disabled desired state."""
    if MOD_SUPPORT.ensure_mod_state(server)["autoapply"]:
        MOD_SUPPORT.apply_configured_mods(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
    post_download_hook=apply_automatic_mods,
)
install.__doc__ = "Download the Space Engineers server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
    post_download_hook=apply_automatic_mods,
)
update.__doc__ = "Update the Space Engineers server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Space Engineers server."


def prestart(server):
    """Revalidate native world activation before launching the engine."""
    sync_server_config(server)
    apply_automatic_mods(server)
    if (IS_LINUX and proton.find_wine()
            and runtime_module.resolve_runtime_metadata(server).get("runtime") == "process"):
        proton.prepare_wineprefix(_wineprefix(server))


def _wineprefix(server):
    """Use a private Wine prefix for each managed dedicated server."""
    return server.data.get("wineprefix") or os.path.join(server.data["dir"], ".alphagsm-wineprefix")


def _wine_launch_options(server):
    """Keep an existing Proton compatibility directory on its original layout."""
    prefix = _wineprefix(server)
    native_prefix = os.path.join(prefix, "pfx")
    if os.path.isfile(os.path.join(native_prefix, "system.reg")):
        if proton.find_proton():
            return {"wineprefix": prefix, "prefer_proton": True}
        return {"wineprefix": native_prefix, "prefer_proton": False}
    return {"wineprefix": prefix, "prefer_proton": False}


def get_start_command(server):
    """Build the command used to launch a Space Engineers dedicated server."""

    executable = _resolve_executable_name(server)
    exe_path = os.path.join(server.data["dir"], executable)
    working_dir = os.path.dirname(exe_path) or server.data["dir"]
    cmd = [
        os.path.basename(executable),
        "-noconsole" if IS_LINUX else "-console",
        "-path",
        _data_path(server),
        "-port",
        str(server.data["port"]),
        "-start",
    ]
    if IS_LINUX:
        cmd = proton.wrap_xvfb_command(
            cmd,
            **_wine_launch_options(server),
        )
    return cmd, working_dir


def get_query_address(server):
    """Return the validated runtime query surface for Space Engineers."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the address used by AlphaGSM info for Space Engineers."""

    return get_query_address(server)


def do_stop(server, j):
    """Stop Space Engineers using the standard exit command."""

    runtime_module.send_to_server(server, "\nexit\n")


def status(server, verbose):
    """Detailed Space Engineers status is not implemented yet."""


def message(server, msg):
    """Space Engineers has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Space Engineers server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Space Engineers datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "maxplayers"),
        str_keys=("exe_name", "dir", "servername", "wineprefix"),
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=({"key": "port", "protocol": "udp"},),
    extra_env=_container_runtime_env,
    extra_host_dependencies=(proton.xvfb_host_dependency(),),
)

def get_container_spec(server):
    """Keep the Wine data directory inside the mounted installation."""

    spec = proton.get_container_spec(
        server, get_start_command,
        port_definitions=({"key": "port", "protocol": "udp"},),
        extra_env=_container_runtime_env(server),
        working_dir=CONTAINER_WORKING_DIR,
    )
    # Wine's Z: drive maps the container filesystem, not the manager's host.
    path_index = spec["command"].index("-path") + 1
    spec["command"][path_index] = "Z:" + proton.CONTAINER_SERVER_DIR.replace("/", "\\")
    return spec
