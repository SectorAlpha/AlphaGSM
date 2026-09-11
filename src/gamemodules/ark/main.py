"""ARK: Survival Evolved dedicated server lifecycle helpers."""

import os
import shlex

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common

steam_app_id = 376030
steam_anonymous_login_possible = True
CONTAINER_STEAMCMD_DIR = "/opt/alphagsm-steamcmd"

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The game port to use for the ARK server",
    "The directory to install ARK in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the ARK: Survival Evolved dedicated server to the latest version.",
    "Restart the ARK: Survival Evolved dedicated server.",
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
    """Return a launch-safe session name for ARK's URL-style map argument."""

    return str(server.data["sessionname"]).replace(" ", "_")


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    exe_name="ShooterGame/Binaries/Linux/ShooterGameServer",
):
    """Collect and store configuration values for an ARK server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "map": "TheIsland",
            "sessionname": "AlphaGSM %s" % (server.name,),
            "adminpassword": "alphagsm",
            "serverpassword": "",
            "maxplayers": "70",
            "queryport": "27015",
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
        default_port=7777,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ARK server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the ARK server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the ARK server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the ARK server."


def get_start_command(server):
    """Build the command used to launch an ARK dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    working_dir = server.data["dir"]
    launcher_relpath = os.path.relpath(exe_path, working_dir)
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
        ["./" + launcher_relpath, map_args, "-server", "-log"],
        working_dir,
    )


def do_stop(server, j):
    """Send the standard quit command to ARK."""

    runtime_module.send_to_server(server, "\nquit\n")


def get_query_address(server):
    """Return ARK's A2S query surface on the managed query port."""

    return (
        runtime_module.resolve_query_host(server),
        int(server.data["queryport"]),
        "a2s",
    )


def get_info_address(server):
    """Return ARK's info surface on the managed query port."""

    return get_query_address(server)


def status(server, verbose):
    """Detailed ARK status is not implemented yet."""


def message(server, msg):
    """ARK has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for an ARK server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported ARK datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport", "maxplayers"),
        str_keys=("map", "sessionname", "adminpassword", "serverpassword", "exe_name", "dir"),
    )

def get_runtime_requirements(server):
    """Return ARK's native Linux Docker runtime contract."""

    mounts = None
    if "dir" in server.data:
        mounts = [
            {
                "source": server.data["dir"],
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
    """Run ARK in Docker as the mounted server-directory owner."""

    requirements = get_runtime_requirements(server)
    command, _cwd = get_start_command(server)
    shell_command = " ".join(shlex.quote(part) for part in command)
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
                + shlex.quote(shell_command)
            ),
        ],
    }
