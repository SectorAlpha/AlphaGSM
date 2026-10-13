"""BrainBread 2-specific lifecycle, configuration, and update helpers."""

from server.modsupport.source_addons import (
        build_source_addon_mod_support,
        load_shared_source_curated_registry,
)
from utils.valve_server import define_valve_server_module
from utils.source_console import build_source_container_start_command
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from server.modsupport.native_workshop import build_native_workshop_support
from .workshop import WORKSHOP_APP_ID, OWNER, apply_workshop
from server.modsupport.native_workshop import safe_server_path
import re


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='BrainBread 2',
    engine='source',
    steam_app_id=475370,
    game_dir='brainbread2',
    executable='srcds_run',
    default_map='bba_barracks',
    max_players=20,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
    enable_map_validation=True,
)
MOD_SUPPORT = build_source_addon_mod_support(
        game_label='BrainBread 2',
        game_dir='brainbread2',
        workshop_app_id=346330,
        cache_namespace='brainbread2',
        direct_url_suffixes={},
        direct_url_filename_description='a supported archive filename',
        curated_registry_loader=load_shared_source_curated_registry,
)

workshop_app_id = WORKSHOP_APP_ID
NATIVE_WORKSHOP = build_native_workshop_support(
    game_label='BrainBread 2', workshop_app_id=workshop_app_id,
    apply_callback=apply_workshop,
)


def mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Preserve archive addons alongside validated native Workshop map packages."""
    if source in ("workshop", "workshop-collection"):
        return NATIVE_WORKSHOP.command_functions["mod"](server, action, source, identifier, extra, **kwargs)
    if action == "apply":
        MOD_SUPPORT.apply_configured_mods(server)
        return NATIVE_WORKSHOP.apply_configured_mods(server)
    if action == "cleanup":
        NATIVE_WORKSHOP.cleanup_configured_mods(server)
        MOD_SUPPORT.cleanup_configured_mods(server)
        NATIVE_WORKSHOP.ensure_mod_state(server)
        return None
    return MOD_SUPPORT.command_functions["mod"](server, action, source, identifier, extra, **kwargs)

steam_app_id = MODULE.steam_app_id
commands = MODULE.commands + MOD_SUPPORT.commands
command_args = {**MODULE.command_args, **MOD_SUPPORT.command_args}
command_descriptions = {**MODULE.command_descriptions, **MOD_SUPPORT.command_descriptions}
command_functions = {**MODULE.command_functions, **MOD_SUPPORT.command_functions}
command_functions["mod"] = mod_command
command_descriptions["mod"] = "Manage archive addons and native Workshop IDs/URLs or collections."
_mod_args = command_args["mod"]
command_args["mod"] = CmdSpec(
    requiredarguments=_mod_args.requiredarguments,
    optionalarguments=(ArgSpec("SOURCE", "manifest/curated, url, gamebanana, moddb, workshop, or workshop-collection", str),
                       *_mod_args.optionalarguments[1:]),
)
max_stop_wait = MODULE.max_stop_wait


def configure(server, ask, port=None, dir=None, *, exe_name=None):
        result = MODULE.configure(server, ask, port, dir, exe_name=exe_name)
        MOD_SUPPORT.ensure_mod_state(server)
        NATIVE_WORKSHOP.ensure_mod_state(server)
        return result


install = MODULE.install
doinstall = MODULE.doinstall
def prestart(server, *args, **kwargs):
    """Reconcile archive addons and validated native maps before launch."""
    MODULE.prestart(server, *args, **kwargs)
    if MOD_SUPPORT.ensure_mod_state(server).get('autoapply', True):
        MOD_SUPPORT.apply_configured_mods(server)
        NATIVE_WORKSHOP.apply_configured_mods(server)

update = MODULE.update
restart = MODULE.restart
get_start_command = MODULE.get_start_command
def _get_container_start_command(server):
    return build_source_container_start_command(server, get_start_command)


do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
def checkvalue(server, key, *value):
    """Include validated installed maps in the upstream native Workshop search path."""
    if key and key[0] in ('map', 'gamemap', 'startmap', 'level', 'worldname') and value:
        name = str(value[0])
        if re.fullmatch(r'[a-zA-Z0-9_-]+', name):
            owned = server.data.get('mods', {}).get('owned_payloads', {}).get(OWNER, {})
            for relative in owned:
                if re.fullmatch(r'brainbread2/workshop/content/346330/[1-9][0-9]*/maps/'
                                + re.escape(name) + r'\.bsp', relative):
                    if safe_server_path(server, relative).is_file():
                        return name
    return MODULE.checkvalue(server, key, *value)


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=_get_container_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
        stdin_open=True,
)
