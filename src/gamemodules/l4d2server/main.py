"""Left 4 Dead 2-specific lifecycle, configuration, and update helpers."""

import os
from pathlib import Path

from server.modsupport.source_addons import build_source_addon_mod_support
from server.modsupport.registry import CuratedRegistryLoader
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


def _assert_required_server_tree(install_dir):
    """Raise when the staged Left 4 Dead 2 server tree is not present locally."""

    required_exe = os.path.join(install_dir, "srcds_run")
    required_map = os.path.join(install_dir, "left4dead2", "maps", "c5m1_waterfront.bsp")
    if os.path.isfile(required_exe) and os.path.isfile(required_map):
        return
    gamemodule_common.raise_byo_requirement(
        "l4d2server",
        "a staged native Left 4 Dead 2 dedicated server tree",
        actions=(
            "Stage a complete Left 4 Dead 2 Linux dedicated server tree into <install_dir>/",
            "Make sure <install_dir>/srcds_run and <install_dir>/left4dead2/maps/c5m1_waterfront.bsp exist before retrying setup/start",
            "Retry setup or start once the staged server files are present locally",
        ),
        docs_slug="l4d2server",
    )


def install(server):
    """Install the anonymous payload when possible, otherwise require a staged tree."""

    if os.path.isfile(os.path.join(server.data["dir"], "srcds_run")):
        MODULE.sync_server_config(server)
        _assert_required_server_tree(server.data["dir"])
        return
    try:
        MODULE.install(server)
    except Exception:
        _assert_required_server_tree(server.data["dir"])
        raise
    _assert_required_server_tree(server.data["dir"])


doinstall = MODULE.doinstall
prestart = MODULE.prestart
update = MODULE.update
restart = MODULE.restart


def get_start_command(server):
    """Build the start command after validating the staged server tree."""

    _assert_required_server_tree(server.data["dir"])
    return MODULE.get_start_command(server)


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
