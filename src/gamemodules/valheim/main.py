"""Valheim dedicated server lifecycle helpers."""

import os
from pathlib import Path
import re

import utils.steamcmd as steamcmd
from utils.backups import backups as backup_utils

import server.runtime as runtime_module
from server.modsupport.registry import CuratedRegistryLoader
from server.modsupport.source_addons import build_source_addon_mod_support
from server.settable_keys import SettingSpec
from utils.gamemodules import common as gamemodule_common


def load_curated_registry():
    """Load the pinned Valheim framework manifest."""

    override = os.environ.get("ALPHAGSM_VALHEIM_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


MOD_SUPPORT = build_source_addon_mod_support(
    game_label="Valheim",
    game_dir=".",
    cache_namespace="valheim",
    direct_url_suffixes={},
    direct_url_filename_description="a supported archive filename",
    allowed_destinations=(
        "BepInEx",
        "doorstop_config.ini",
        "libdoorstop.so",
        "run_bepinex.sh",
        "changelog.txt",
    ),
    enabled_sources=(),
    curated_registry_loader=load_curated_registry,
    curated_identifier_description="framework name",
)

steam_app_id = 896660
steam_anonymous_login_possible = True

commands = ("update", "restart") + MOD_SUPPORT.commands
command_args = gamemodule_common.build_setup_update_restart_command_args(
    "The port for the server to listen on",
    "The directory to install Valheim in",
)
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    "Update the Valheim dedicated server to the latest version.",
    "Restart the Valheim dedicated server.",
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions = dict(MOD_SUPPORT.command_functions)
setting_schema = {
    "serverpassword": SettingSpec(
        canonical_key="serverpassword",
        description="Password required to join the server.",
        secret=True,
    ),
}
max_stop_wait = 1


def configure(server, ask, port=None, dir=None, *, exe_name="valheim_server.x86_64"):
    """Collect and store configuration values for a Valheim server."""

    gamemodule_common.set_steam_install_metadata(
        server,
        steam_app_id=steam_app_id,
        steam_anonymous_login_possible=steam_anonymous_login_possible,
    )
    gamemodule_common.set_server_defaults(
        server,
        {
            "servername": "AlphaGSM %s" % (server.name,),
            "worldname": server.name,
            "serverpassword": "alphagsm",
            "public": "0",
        },
    )
    gamemodule_common.ensure_backup_config(
        server,
        backupfiles=["worlds", "start_server.sh"],
        targets=["worlds"],
    )
    gamemodule_common.configure_port(
        server,
        ask,
        port,
        default_port=2456,
        prompt="Please specify the port to use for this server:",
    )
    server.data.setdefault("queryport", str(int(server.data["port"]) + 1))
    gamemodule_common.configure_install_dir(
        server,
        ask,
        dir,
        prompt="Where would you like to install the Valheim server:",
    )
    gamemodule_common.configure_executable(server, exe_name=exe_name)
    MOD_SUPPORT.ensure_mod_state(server)
    return gamemodule_common.finalize_configure(server)


install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
install.__doc__ = "Download the Valheim dedicated server files via SteamCMD."


update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=steam_anonymous_login_possible,
)
update.__doc__ = "Update the Valheim server files and optionally restart the server."


restart = gamemodule_common.make_restart_hook()
restart.__doc__ = "Restart the Valheim server."


def get_wipe_paths(server):
    """Return the Valheim world directory created by -savedir."""

    del server
    return ["worlds"]


def get_hard_wipe_preserve_paths(server):
    """Keep Valheim permission lists across a reinstall."""

    del server
    return ["adminlist.txt", "bannedlist.txt", "permittedlist.txt"]


def _prepare_bepinex_launcher(server, exe_name):
    """Point an installed BepInEx script at the dedicated-server executable."""

    install_dir = os.path.abspath(server.data["dir"])
    script = os.path.join(install_dir, "run_bepinex.sh")
    if not os.path.isfile(script) or os.path.islink(script):
        return None
    with open(script, "r", encoding="utf-8") as handle:
        text = handle.read()
    updated, count = re.subn(
        r'(?m)^executable_name=.*$',
        'executable_name="%s"' % exe_name,
        text,
        count=1,
    )
    if count and updated != text:
        with open(script, "w", encoding="utf-8") as handle:
            handle.write(updated)
    mode = os.stat(script).st_mode
    if mode & 0o111 != 0o111:
        os.chmod(script, mode | 0o111)
    return script


def get_start_command(server):
    """Build the command used to launch a Valheim dedicated server."""

    install_dir = os.path.abspath(server.data["dir"])
    exe_path = gamemodule_common.resolve_install_executable(server)
    working_dir = os.path.dirname(exe_path) or install_dir
    bepinex = _prepare_bepinex_launcher(server, os.path.basename(exe_path))
    if server.data.get("runtime") == "docker":
        savedir = os.path.relpath(os.path.join(install_dir, "worlds"), working_dir)
        savedir = savedir.replace("\\", "/")
        if not savedir.startswith("."):
            savedir = "./" + savedir
    else:
        savedir = os.path.join(install_dir, "worlds")
    if bepinex and os.path.dirname(bepinex) == working_dir:
        launch_name = "./run_bepinex.sh"
    else:
        launch_name = "./" + os.path.basename(exe_path)
    return (
        [
            launch_name,
            "-name",
            server.data["servername"],
            "-port",
            str(server.data["port"]),
            "-world",
            server.data["worldname"],
            "-password",
            server.data["serverpassword"],
            "-savedir",
            savedir,
            "-public",
            server.data["public"],
            "-batchmode",
            "-nographics",
        ],
        working_dir,
    )


def do_stop(server, j):
    """Send an interrupt-style stop request to Valheim."""

    runtime_module.send_to_server(server, "\003")


def status(server, verbose):
    """Detailed Valheim status is not implemented yet."""


def message(server, msg):
    """Valheim has no simple generic message console support here."""

    gamemodule_common.print_unsupported_message()


def backup(server, profile=None):
    """Run the shared backup implementation for a Valheim server."""

    gamemodule_common.run_backup(server, profile, backup_module=backup_utils)


def get_query_address(server):
    """Return Valheim's documented primary UDP health surface."""

    return (runtime_module.resolve_query_host(server), int(server.data["port"]), "udp")


def get_info_address(server):
    """Return the same UDP health surface used by the info command."""

    return get_query_address(server)


def checkvalue(server, key, *value):
    """Validate supported Valheim datastore edits."""

    return gamemodule_common.handle_basic_checkvalue(
        server,
        key,
        *value,
        int_keys=("port", "queryport"),
        str_keys=("servername", "worldname", "serverpassword", "public", "exe_name", "dir"),
        backup_module=backup_utils,
    )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'queryport', 'protocol': 'udp'}, {'key': 'queryport', 'protocol': 'tcp'}),
        stdin_open=True,
)
