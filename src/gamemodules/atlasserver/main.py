"""ATLAS dedicated server lifecycle helpers."""

import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1006030
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ATLAS server",
    "The directory to install ATLAS in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the ATLAS dedicated server to the latest version.",
    "Restart the ATLAS dedicated server.",
)
command_functions = {}
setting_schema = {
    "adminpassword": SettingSpec(
        canonical_key="adminpassword",
        description="Server admin password.",
        secret=True,
    ),
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required to join the server.",
        secret=True,
    ),
}
max_stop_wait = 1


def _launch_session_name(server):
    """Return a launch-safe session name for ATLAS' URL-style map argument."""

    return str(server.data["sessionname"]).replace(" ", "_")


def _server_grid_paths(server):
    """Return the ATLAS grid export files and directory expected at runtime."""

    shooter_dir = os.path.join(server.data["dir"], "ShooterGame")
    return (
        os.path.join(shooter_dir, "ServerGrid.json"),
        os.path.join(shooter_dir, "ServerGrid.ServerOnly.json"),
        os.path.join(shooter_dir, "ServerGrid"),
    )


def _ensure_server_grid_export(server):
    """Fail fast when the required ATLAS server-grid export is missing."""

    grid_json, grid_server_only, grid_dir = _server_grid_paths(server)
    missing = [
        path
        for path in (grid_json, grid_server_only, grid_dir)
        if not (os.path.isfile(path) or os.path.isdir(path))
    ]
    if not missing:
        return

    gamemodule_common.raise_byo_requirement(
        "atlasserver",
        "a staged ATLAS server-grid export",
        actions=(
            "Generate or export ServerGrid.json, ServerGrid.ServerOnly.json, and the ServerGrid folder with the official ServerGridEditor.",
            f"Copy those three items into {os.path.join(server.data['dir'], 'ShooterGame')}.",
            "Retry start once the grid export is staged.",
        ),
        docs_slug="atlasserver",
    )


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="ShooterGame/Binaries/Linux/ShooterGameServer",
):
    """Collect and store configuration values for an ATLAS server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "map": "Ocean",
            "sessionname": "AlphaGSM %s" % (server.name,),
            "serverpassword": "",
            "adminpassword": "alphagsm",
            "maxplayers": "100",
            "queryport": "57561",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["ShooterGame/Saved", "ShooterGame/Saved/Config/LinuxServer"],
        targets=["ShooterGame/Saved"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=57555,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ATLAS server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the ATLAS server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the ATLAS server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the ATLAS server."


def prestart(server):
    """Require the staged ATLAS grid export before launch."""

    _ensure_server_grid_export(server)


def get_query_address(server):
    """ATLAS uses Steam A2S on the dedicated query port."""

    return (runtime_module.resolve_query_host(server), int(server.data["queryport"]), "a2s")


def get_info_address(server):
    """Return the A2S address used by the info command."""

    return get_query_address(server)


def _build_start_command(server, *, validate_grid):
    """Build the command used to launch an ATLAS dedicated server."""

    install_dir = os.path.normpath(server.data["dir"])
    exe_path = os.path.join(install_dir, server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    if validate_grid:
        _ensure_server_grid_export(server)
    working_dir = os.path.dirname(exe_path) or install_dir
    map_args = (
        "%s?listen?SessionName=%s?Port=%s?QueryPort=%s?MaxPlayers=%s?ServerAdminPassword=%s"
        % (
            server.data["map"],
            _launch_session_name(server),
            server.data["port"],
            server.data["queryport"],
            server.data["maxplayers"],
            server.data["adminpassword"],
        )
    )
    if server.data["serverpassword"]:
        map_args += "?ServerPassword=%s" % (server.data["serverpassword"],)
    return (
        ["./" + os.path.basename(server.data["exe_name"]), map_args, "-server", "-log"],
        working_dir,
    )


def get_start_command(server):
    """Build the command used to launch an ATLAS dedicated server."""

    return _build_start_command(server, validate_grid=True)


def do_stop(server, j):
    """Send the standard quit command to ATLAS."""

    runtime_module.send_to_server(server, "\nquit\n")


def status(server, verbose):
    """Detailed ATLAS status is not implemented yet."""


def message(server, msg):
    """ATLAS has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ATLAS server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ATLAS datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("map", "sessionname", "serverpassword", "adminpassword", "exe_name", "dir"),
    )

def get_runtime_requirements(server):
    """Return ATLAS' native Linux Docker runtime contract."""

    mounts = None
    if "dir" in server.data:
        mounts = [
            {
                "source": os.path.normpath(server.data["dir"]),
                "target": "/srv/server",
                "mode": "rw",
            },
            {
                "source": os.path.normpath(steamcmd.STEAMCMD_DIR),
                "target": CONTAINER_STEAMCMD_DIR,
                "mode": "ro",
            },
        ]

    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=(
            {"key": "queryport", "protocol": "udp"},
            {"key": "queryport", "protocol": "tcp"},
            {"key": "port", "protocol": "udp"},
            {"key": "port", "protocol": "tcp"},
        ),
        mounts=mounts,
    )

def get_container_spec(server):
    """Run ATLAS in Docker as the mounted server-directory owner."""

    requirements = get_runtime_requirements(server)
    command, cwd = _build_start_command(server, validate_grid=False)
    shell_command = " ".join(shlex.quote(part) for part in command)
    relative_cwd = os.path.relpath(cwd, os.path.normpath(server.data["dir"]))
    container_cwd = "/srv/server"
    if relative_cwd not in (".", ""):
        container_cwd = "/srv/server/" + relative_cwd
    user_shell_command = "cd " + shlex.quote(container_cwd) + " && " + shell_command
    return {
        "working_dir": "/srv/server",
        "stdin_open": True,
        "tty": False,
        "env": requirements.get("env", {}),
        "mounts": requirements.get("mounts", []),
        "ports": requirements.get("ports", []),
        "command": [
            "sh",
            "-lc",
            (
                'id -u alphagsm >/dev/null 2>&1 || useradd -M -u 1000 -o alphagsm; '
                'mkdir -p /home/alphagsm/.steam/sdk64; '
                'chmod -R a+rwX /srv/server /home/alphagsm; '
                'ln -sfn '
                + CONTAINER_STEAMCMD_DIR
                + '/linux64/steamclient.so /home/alphagsm/.steam/sdk64/steamclient.so; '
                'export HOME=/home/alphagsm USER=alphagsm LOGNAME=alphagsm; '
                "exec runuser -u alphagsm -- sh -lc "
                + shlex.quote(user_shell_command)
            ),
        ],
    }
