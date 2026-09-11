"""Left 4 Dead 2-specific lifecycle, configuration, and update helpers."""

import os
from pathlib import Path
from server.modsupport.source_addons import build_source_addon_mod_support
from server.modsupport.registry import CuratedRegistryLoader
import utils.steamcmd as steamcmd
from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Left 4 Dead 2',
    engine='source',
    steam_app_id=222860,
    game_dir='left4dead2',
    executable='srcds_run',
    default_map='c5m1_waterfront',
    max_players=8,
    port=27015,
    client_port=27005,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
    enable_map_validation=True,
)


def load_curated_registry():
    override = os.environ.get("ALPHAGSM_L4D2_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


MOD_SUPPORT = build_source_addon_mod_support(
    game_label="Left 4 Dead 2",
    game_dir="left4dead2",
    cache_namespace="left4dead2",
    direct_url_suffixes={".vpk": "single"},
    direct_url_filename_description="a .vpk addon filename or a supported archive filename",
    curated_registry_loader=load_curated_registry,
)

steam_app_id = MODULE.steam_app_id
commands = MODULE.commands + MOD_SUPPORT.commands
command_args = {**MODULE.command_args, **MOD_SUPPORT.command_args}
command_descriptions = {**MODULE.command_descriptions, **MOD_SUPPORT.command_descriptions}
command_functions = {**MODULE.command_functions, **MOD_SUPPORT.command_functions}
max_stop_wait = MODULE.max_stop_wait


def configure(server, ask, port=None, dir=None, *, exe_name=None):
    result = MODULE.configure(server, ask, port, dir, exe_name=exe_name)
    MOD_SUPPORT.ensure_mod_state(server)
    return result


def _finalize_source_install(server):
    """Apply the standard Valve Source install cleanup after SteamCMD."""

    if os.path.isfile(os.path.join(server.data["dir"], "srcds_run_64")):
        server.data["exe_name"] = "srcds_run_64"

    for script_name in ("srcds_run", "srcds_run.sh", os.path.join("bin", "srcds_run.sh")):
        script_path = os.path.join(server.data["dir"], script_name)
        if not os.path.isfile(script_path):
            continue
        with open(script_path, "rb") as handle:
            content = handle.read()
        if content.startswith(b"#!") and b"\r\n" in content:
            with open(script_path, "wb") as handle:
                handle.write(content.replace(b"\r\n", b"\n"))

def _download_l4d2_server(server, validate):
    """Install the L4D2 dedicated payload by layering Windows then Linux depots.

    Valve's current anonymous SteamCMD path for app 222860 rejects a
    Linux-only install with ``Invalid platform``. The documented workaround is
    to stage the Windows depots first, then apply the Linux depots into the
    same install tree.
    """

    for force_platform in ("windows", "linux"):
        steamcmd.download(
            server.data["dir"],
            steam_app_id,
            True,
            validate=validate,
            force_platform=force_platform,
        )


def _finish_l4d2_install(server):
    """Run the normal Source post-install steps for the staged server tree."""

    _finalize_source_install(server)
    MODULE.sync_server_config(server)


def doinstall(server):
    _download_l4d2_server(server, validate=True)


def install(server):
    _download_l4d2_server(server, validate=False)
    _finish_l4d2_install(server)


prestart = MODULE.prestart


def update(server, validate=False, restart=False):
    _download_l4d2_server(server, validate=validate)
    _finish_l4d2_install(server)
    if restart:
        MODULE.restart(server)


restart = MODULE.restart
get_start_command = MODULE.get_start_command


do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}),
        stdin_open=True,
)
