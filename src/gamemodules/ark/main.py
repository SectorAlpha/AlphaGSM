"""ARK: Survival Evolved dedicated server lifecycle helpers."""

import os

import utils.steamcmd as steamcmd
from server import ServerError

import server.runtime as runtime_module
from server.settable_keys import SettingSpec
from utils.backups import backups as backup_utils
from utils.gamemodules import common as gamemodule_common
from server.modsupport.native_workshop import build_native_workshop_support
from .workshop import configure_workshop, configured_workshop_ids, refresh_launch_workshop_ids

steam_app_id = 376030
steam_anonymous_login_possible = True
workshop_app_id = 346110

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
_mod_support = build_native_workshop_support(
    game_label="ARK: Survival Evolved", workshop_app_id=workshop_app_id,
    apply_callback=configure_workshop,
)
commands += _mod_support.commands
command_args.update(_mod_support.command_args)
command_descriptions.update(_mod_support.command_descriptions)
command_functions.update(_mod_support.command_functions)
ensure_mod_state = _mod_support.ensure_mod_state
apply_configured_mods = _mod_support.apply_configured_mods
cleanup_configured_mods = _mod_support.cleanup_configured_mods
setting_schema = {
    "rconenabled": SettingSpec(canonical_key="rconenabled", value_type="boolean",
                               description="Enable native RCON after setting a private admin password.",
                               apply_to=("datastore", "launch_args")),
    "rconport": SettingSpec(canonical_key="rconport", value_type="integer",
                            description="Native RCON TCP port.",
                            apply_to=("datastore", "launch_args")),
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
_PORT_DEFINITIONS = (
    {"key": "queryport", "protocol": "udp"},
    {"key": "queryport", "protocol": "tcp"},
    {"key": "port", "protocol": "udp"},
    {"key": "port", "protocol": "tcp"},
    {"key": "port", "offset": 1, "protocol": "udp"},
    {"key": "rconport", "protocol": "tcp"},
)
port_claim_definitions = _PORT_DEFINITIONS


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
    server.data.setdefault("rconenabled", False)
    server.data.setdefault("rconport", str(server.data["port"] + 2))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the ARK server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    return gamemodule_common.finalize_configure(server)


_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
def install(server):
    """Install ARK and reconcile desired native Workshop gameplay mods."""
    _install(server)
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the ARK server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the ARK server."


def prestart(server):
    """Reconcile native descriptors, decompressed assets and ActiveMods before start."""
    if ensure_mod_state(server).get("autoapply", True):
        apply_configured_mods(server)
    refresh_launch_workshop_ids(server)


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
    workshop_ids = configured_workshop_ids(server)
    if workshop_ids:
        map_args += "?GameModIds=" + ",".join(workshop_ids)
    if server.data.get("rconenabled", False):
        _rcon_enabled(server, "true")
        map_args += "?RCONEnabled=True?RCONPort=" + str(int(server.data["rconport"]))
    return (
        ["./" + launcher_relpath, map_args, "-server", "-log", "-stdout",
         "-FullStdOutLogOutput", "-forcelogflush"],
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
        int_keys=("port", "queryport", "rconport", "maxplayers"),
        custom_handlers={"rconenabled": _rcon_enabled},
        str_keys=("map", "sessionname", "adminpassword", "serverpassword", "exe_name", "dir"),
    )


def _rcon_enabled(server, value):
    """Keep local native RCON opt-in and require a private password."""
    lowered = str(value).lower()
    if lowered not in ("true", "false", "1", "0", "yes", "no"):
        raise ServerError("rconenabled must be true or false")
    enabled = lowered in ("true", "1", "yes")
    if enabled and server.data.get("adminpassword", "") in ("", "alphagsm"):
        raise ServerError("Set a private adminpassword before enabling RCON")
    return enabled

def get_runtime_requirements(server):
    """Return ARK's native Linux Docker runtime contract."""
    return runtime_module.build_runtime_requirements(
        server,
        family="steamcmd-linux",
        port_definitions=_PORT_DEFINITIONS,
        extra={"run_as_host_user": True, "container_home": "/home/alphagsm"},
    )


def get_container_spec(server):
    """Run ARK in Docker as the mounted server-directory owner."""

    return runtime_module.build_container_spec(
        server, family="steamcmd-linux", get_start_command=get_start_command,
        port_definitions=_PORT_DEFINITIONS, stdin_open=True,
        extra={"run_as_host_user": True, "container_home": "/home/alphagsm"},
    )
