"""Necesse dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from utils.backups import backups as backup_utils
from utils.cmdparse.cmdspec import CmdSpec, OptSpec
from utils.gamemodules import common as gamemodule_common

steam_app_id = 1169370
steam_anonymous_login_possible = True

commands = ("update", "restart")
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Necesse in",
)
command_args["start"] = CmdSpec(options=(
    OptSpec((), ("autocreate",), "Create the configured world only if it is missing",
            "autocreate", None, True),
))
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Necesse dedicated server to the latest version.",
    "Restart the Necesse dedicated server.",
)
command_functions = {}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="Server.jar", javapath="java"):
    """Collect and store configuration values for a Necesse server."""

    first_setup = "Steam_AppID" not in server.data
    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "slots": "10",
            "world": server.name,
            "javapath": javapath,
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["cfg", "saves", "mods", "Server.jar"],
        targets=["cfg", "saves", "mods"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=14159,
        prompt="Please specify the port to use for this server:",
    )
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Necesse server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    if first_setup:
        server.data.setdefault("datadir", server.data["dir"])
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Necesse server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)


restart = gamemodule_common.make_restart_hook()


def _data_dir(server):
    """Resolve the native save directory against the server launch directory."""

    datadir = server.data.get("datadir")
    if not datadir:
        return None
    return os.path.abspath(os.path.join(server.data["dir"], os.path.expanduser(datadir)))


def _world_creation_args(server, autocreate):
    """Create only a missing save in a known, persistent data directory."""

    if not autocreate:
        return []
    datadir = _data_dir(server)
    if not datadir:
        raise ServerError(
            "Set datadir to the existing Necesse data directory before using --autocreate"
        )
    if any(os.path.lexists(os.path.join(datadir, path)) for path in get_wipe_paths(server)):
        return []
    return ["-world", server.data["world"]]


def get_wipe_root(server):
    """Resolve the explicit save location instead of guessing a legacy home path."""

    datadir = _data_dir(server)
    if not datadir:
        raise ServerError("Set datadir to the existing Necesse data directory before wipe")
    return datadir


def get_wipe_paths(server):
    """Return this world's compressed/uncompressed saves in the data directory."""

    world = server.data["world"]
    if not world or world in (".", "..") or "/" in world or "\\" in world:
        raise ServerError("World operations require a single configured Necesse world name")
    paths = [os.path.join(directory, name)
             for directory in ("saves", os.path.join("saves", "worlds"))
             for name in (world, world + ".zip")]
    # Newer saves/worlds is a container of saves, never a single world target.
    return [path for path in paths if path != os.path.join("saves", "worlds")]


def get_start_command(server, *, autocreate=False):
    """Build the command used to launch a Necesse dedicated server."""

    exe_path = os.path.join(server.data["dir"], server.data["exe_name"])
    if not os.path.isfile(exe_path):
        raise ServerError("Executable file not found")
    command = [
        server.data["javapath"],
        "-jar",
        server.data["exe_name"],
        "-nogui",
        "-port",
        str(server.data["port"]),
        "-slots",
        str(server.data["slots"]),
    ]
    if server.data.get("datadir"):
        command.extend(["-datadir", _data_dir(server)])
    command.extend(_world_creation_args(server, autocreate))
    return command, server.data["dir"]


def get_query_address(server):
    """Necesse exposes a UDP game port without a richer public query protocol."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the UDP address used by the info command."""
    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def do_stop(server, j):
    """Stop Necesse using the standard console command."""

    runtime_module.send_to_server(server, "\nstop\n")


def status(server, verbose):
    """Detailed Necesse status is not implemented yet."""


def message(server, msg):
    """Necesse has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Necesse server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def checkvalue(server, key, *value):
    """Validate supported Necesse datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "slots"),
        str_keys=("servername", "world", "javapath", "exe_name", "dir", "datadir"),
    )

def get_runtime_requirements(server):
    java_major = server.data.get("java_major")
    if java_major is None:
        java_major = runtime_module.infer_minecraft_java_major(
            server.data.get("version")
        )
    mounts = None
    if _data_dir(server):
        mounts = [
            {"source": server.data["dir"], "target": "/srv/server", "mode": "rw"},
            {"source": _data_dir(server), "target": "/srv/necesse-data", "mode": "rw"},
        ]
    return runtime_module.build_runtime_requirements(
        server,
        family="java",
        mounts=mounts,
        port_definitions=({'key': 'port', 'protocol': 'udp'},),
        env={
            "ALPHAGSM_JAVA_MAJOR": str(java_major),
            "ALPHAGSM_SERVER_JAR": server.data.get("exe_name", "server.jar"),
        },
        extra={"java": int(java_major)},
    )

def get_container_spec(server, *, autocreate=False):
    requirements = get_runtime_requirements(server)
    spec = runtime_module.build_container_spec(
        server,
        family="java",
        get_start_command=lambda current: get_start_command(current, autocreate=autocreate),
        port_definitions=({'key': 'port', 'protocol': 'udp'},),
        env=requirements.get("env", {}),
        mounts=requirements.get("mounts"),
        stdin_open=True,
        tty=True,
    )
    if _data_dir(server):
        spec["command"][spec["command"].index("-datadir") + 1] = "/srv/necesse-data"
    return spec
