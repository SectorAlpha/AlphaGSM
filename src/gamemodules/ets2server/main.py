"""Euro Truck Simulator 2 dedicated server lifecycle helpers."""

import os
import re

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1948160
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port for the server to listen on",
    "The directory to install Euro Truck Simulator 2 in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Euro Truck Simulator 2 dedicated server to the latest version.",
    "Restart the Euro Truck Simulator 2 dedicated server.",
)
command_functions = {}
max_stop_wait = 1
config_sync_keys = ("port", "queryport")


def _server_home_dir(server):
    """Return the instance's directory for exported packages and native config."""

    return os.path.join(
        server.data["dir"],
        server.data.get("configdir", ".local/share/Euro Truck Simulator 2"),
    )


def _xdg_data_home(server):
    """Keep Linux's required game subdirectory compatible with custom configdir."""

    home_dir = os.path.abspath(_server_home_dir(server))
    if os.path.basename(home_dir) == "Euro Truck Simulator 2":
        return os.path.dirname(home_dir)
    return os.path.join(server.data["dir"], ".alphagsm", "ets2-user-data")


def sync_server_config(server):
    """Keep native dedicated ports aligned while retaining operator settings."""

    home_dir = _server_home_dir(server)
    os.makedirs(home_dir, exist_ok=True)
    path = os.path.join(home_dir, "server_config.sii")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
    else:
        content = "SiiNunit\n{\nserver_config : _nameless.alphagsm {\n}\n}\n"
    for key, value in (
        ("connection_dedicated_port", server.data.get("port", 27015)),
        ("query_dedicated_port", server.data.get("queryport", 27016)),
    ):
        pattern = r"(?m)^[ \t]*" + key + r"[ \t]*:[^\n]*"
        replacement = " " + key + ": " + str(int(value))
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
        else:
            content, count = re.subn(r"(?m)^[ \t]*}", replacement + "\n}", content, count=1)
            if not count:
                raise ServerError("Invalid ETS2 server_config.sii: missing closing brace")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    native_path = os.path.join(_xdg_data_home(server), "Euro Truck Simulator 2")
    if os.path.abspath(native_path) != os.path.abspath(home_dir):
        os.makedirs(os.path.dirname(native_path), exist_ok=True)
        if os.path.islink(native_path):
            os.unlink(native_path)
        if os.path.lexists(native_path):
            raise ServerError("ETS2 managed user path is occupied: " + native_path)
        os.symlink(os.path.abspath(home_dir), native_path, target_is_directory=True)


def prestart(server):
    """Require genuine client exports before launching the dedicated server."""

    home_dir = _server_home_dir(server)
    paths = [os.path.join(home_dir, name) for name in ("server_packages.sii", "server_packages.dat")]
    if any(not os.path.isfile(path) or os.path.getsize(path) == 0 for path in paths):
        gamemodule_common.raise_byo_requirement(
            "ets2server",
            "exported ETS2 server packages/settings from an owned client install",
            actions=(
                "Run export_server_packages from an owned Euro Truck Simulator 2 client.",
                f"Copy server_packages.sii and server_packages.dat into {home_dir}.",
                "Retry start once both exported files are staged.",
            ),
            docs_slug="ets2server",
        )
    sync_server_config(server)


def configure(server, ask, port=None, dir=None, *, exe_name="bin/linux_x64/eurotrucks2_server"):
    """Collect and store configuration values for an ETS2 server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "queryport": "27016",
            "configdir": ".local/share/Euro Truck Simulator 2",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=[".local/share/Euro Truck Simulator 2"],
        targets=[".local/share/Euro Truck Simulator 2"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=27015,
        prompt="Please specify the game port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Euro Truck Simulator 2 server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)
install.__doc__ = "Download the ETS2 server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
    sync_server_config=sync_server_config,
)

restart = gamemodule_common.make_restart_hook()


def get_query_address(server):
    """ETS2 uses Steam A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_start_command(server):
    """Build the command used to launch an ETS2 dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    return (
        [
            "env",
            "XDG_DATA_HOME=" + _xdg_data_home(server),
            "./" + server.data["exe_name"],
        ],
        server.data["dir"],
    )


def do_stop(server, j):
    """Stop ETS2 by interrupting the foreground process."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    try:
        if verbose:
            server.info(as_json=False, detailed=False)
        else:
            server.query()
    except Exception as exc:
        print("Status check failed: " + str(exc))
status.__doc__ = "Detailed ETS2 status is not implemented yet."


def message(server, msg):
    """ETS2 has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ETS2 server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ETS2 datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("configdir", "exe_name", "dir"),
    )

def _runtime_mounts(server):
    """Extend the Steam SDK mounts before shared path validation and mapping."""

    mounts = runtime_module.build_runtime_requirements(server, family="steamcmd-linux").get("mounts", [])
    if not server.data.get("dir"):
        return mounts
    mounts.append({"source": _server_home_dir(server), "target": "/srv/ets2-data/Euro Truck Simulator 2", "mode": "rw"})
    return mounts


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}, {'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        mounts=_runtime_mounts,
)

def get_container_spec(server):
    """Mount exported packages and config at a stable container-visible path."""

    spec = runtime_module.build_container_spec(
        server,
        family="steamcmd-linux",
        get_start_command=get_start_command,
        mounts=_runtime_mounts(server),
        port_definitions=(
            {"key": "queryport", "protocol": "udp"},
            {"key": "queryport", "protocol": "tcp"},
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        stdin_open=True,
    )
    spec["command"][1] = "XDG_DATA_HOME=/srv/ets2-data"
    return spec
