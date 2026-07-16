"""ASTRONEER dedicated server lifecycle helpers."""

import os

import utils.proton as proton
import utils.steamcmd as steamcmd
from server import ServerError
from utils.backups import backups as backup_utils
from utils.simple_kv_config import rewrite_equals_config

from utils.platform_info import IS_LINUX

import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

steam_app_id = 728470
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ASTRONEER server",
    "The directory to install ASTRONEER in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the ASTRONEER dedicated server to the latest version.",
    "Restart the ASTRONEER dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "publicip", "ownername")


def _container_runtime_env(_server):
    """Return the Docker runtime env needed for Astroneer's UE4 prereqs."""

    return {
        "ALPHAGSM_XVFB": "1",
        "ALPHAGSM_XVFB_DISPLAY": ":99",
        "ALPHAGSM_XVFB_SERVER_ARGS": "-screen 0 1024x768x24 -nolisten tcp",
        "SDL_VIDEODRIVER": "x11",
        "SDL_AUDIODRIVER": "dummy",
        "WINEDLLOVERRIDES": "",
        "LIBGL_ALWAYS_SOFTWARE": "1",
    }


def configure(server, ask, port=None, dir=None, *, exe_name="AstroServer.exe"):
    """Collect and store configuration values for an ASTRONEER server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "publicip": "127.0.0.1",
            "ownername": "AlphaGSM",
            "servername": "AlphaGSM %s" % (server.name,),
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["Astro/Saved"],
        targets=["Astro/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=8777,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ASTRONEER server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


def _config_dir(server):
    """Return Astroneer's authoritative WindowsServer config directory."""

    return os.path.join(
        server.data["dir"],
        "Astro",
        "Saved",
        "Config",
        "WindowsServer",
    )


def _sync_engine_port(config_path, port):
    """Keep the URL port in Engine.ini while preserving unrelated settings."""

    lines = []
    section_found = False
    port_written = False
    in_url_section = False
    if os.path.isfile(config_path):
        with open(config_path, "r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped.startswith("[") and stripped.endswith("]"):
                    if in_url_section and not port_written:
                        lines.append("Port=%s\n" % (port,))
                        port_written = True
                    in_url_section = stripped.lower() == "[url]"
                    section_found = section_found or in_url_section
                if in_url_section and stripped.lower().startswith("port="):
                    line = "Port=%s\n" % (port,)
                    port_written = True
                lines.append(line)
    if not section_found:
        if lines and lines[-1].strip():
            lines.append("\n")
        lines.append("[URL]\n")
    if not port_written:
        lines.append("Port=%s\n" % (port,))
    with open(config_path, "w", encoding="utf-8") as handle:
        handle.write("".join(lines))


def sync_server_config(server):
    """Write the official Astroneer connection and ownership settings."""

    config_dir = _config_dir(server)
    os.makedirs(config_dir, exist_ok=True)
    _sync_engine_port(
        os.path.join(config_dir, "Engine.ini"),
        int(server.data.get("port", 8777)),
    )
    rewrite_equals_config(
        os.path.join(config_dir, "AstroServerSettings.ini"),
        {
            "PublicIP": server.data.get("publicip", "127.0.0.1"),
            "OwnerName": server.data.get("ownername", "AlphaGSM"),
            "OwnerGuid": 0,
        },
    )


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    download_kwargs={"force_windows": IS_LINUX},
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the ASTRONEER server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
update.__doc__ = "Update the ASTRONEER server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the ASTRONEER server."


def prestart(server):
    """Refresh Astroneer's authoritative INI settings before launch."""

    sync_server_config(server)


def get_query_address(server):
    """ASTRONEER exposes a generic TCP listener on the managed game port."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "tcp")


def get_info_address(server):
    """Return the TCP address used by the info command."""

    return get_query_address(server)


def get_start_command(server):
    """Build the command used to launch an ASTRONEER dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    cmd = [server.data["exe_name"]]
    if IS_LINUX:
        cmd = proton.wrap_command(
            cmd,
            wineprefix=server.data.get("wineprefix"),
            prefer_proton=True,
        )
    return cmd, server.data["dir"]


def do_stop(server, j):
    """Stop the ASTRONEER server by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed ASTRONEER status is not implemented yet."""


def message(server, msg):
    """ASTRONEER has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ASTRONEER server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ASTRONEER datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port",),
        str_keys=("publicip", "ownername", "servername", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=({"key": "port", "protocol": "udp"}, {"key": "port", "protocol": "tcp"}),
    extra_env=_container_runtime_env,
)

get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command,
    port_definitions=({"key": "port", "protocol": "udp"}, {"key": "port", "protocol": "tcp"}),
    extra_env=_container_runtime_env,
)
