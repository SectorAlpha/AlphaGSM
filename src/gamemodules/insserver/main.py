"""Insurgency-specific lifecycle, configuration, and update helpers."""

import os
from pathlib import Path

from server.modsupport.source_addons import build_source_addon_mod_support
from server.modsupport.registry import CuratedRegistryLoader
from utils.valve_server import define_valve_server_module
from utils.source_console import build_source_container_start_command
from utils.cmdparse.cmdspec import ArgSpec, CmdSpec
from server.modsupport.native_workshop import (
    apply_managed_workshop_list, build_native_workshop_support, safe_server_path,
)
import re


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Insurgency',
    engine='source',
    steam_app_id=237410,
    game_dir='insurgency',
    executable='srcds_run',
    default_map='embassy_coop checkpoint',
    max_players=32,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
    enable_map_validation=True,
)


def load_curated_registry():
    override = os.environ.get("ALPHAGSM_INS_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


MOD_SUPPORT = build_source_addon_mod_support(
    game_label="Insurgency",
    game_dir="insurgency",
    cache_namespace="insurgency",
    workshop_app_id=222880,
    direct_url_suffixes={},
    direct_url_filename_description="a supported archive filename",
    curated_registry_loader=load_curated_registry,
)


workshop_app_id = 222880
_WORKSHOP_LIST = "insurgency/subscribed_file_ids.txt"


def apply_workshop_configuration(server, item_ids):
    """Merge only AlphaGSM-owned IDs into the engine's native subscription list."""
    return apply_managed_workshop_list(server, _WORKSHOP_LIST, item_ids)


NATIVE_WORKSHOP = build_native_workshop_support(
    game_label="Insurgency", workshop_app_id=workshop_app_id,
    apply_callback=apply_workshop_configuration,
)


def mod_command(server, action, source=None, identifier=None, extra=None, **kwargs):
    """Preserve archive addons alongside native, no-key Workshop subscriptions."""
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
    """Reconcile archive addons and native Workshop before both runtime launches."""
    MODULE.prestart(server, *args, **kwargs)
    if MOD_SUPPORT.ensure_mod_state(server).get("autoapply", True):
        MOD_SUPPORT.apply_configured_mods(server)
        NATIVE_WORKSHOP.apply_configured_mods(server)

update = MODULE.update
restart = MODULE.restart
def get_start_command(server):
    """Enable native Workshop only when requested or configured by the operator."""
    command, directory = MODULE.get_start_command(server)
    desired = server.data.get("mods", {}).get("desired", {}).get("workshop", [])
    path = safe_server_path(server, _WORKSHOP_LIST)
    operator_ids = False
    if path.is_file():
        if path.stat().st_size > 1024 * 1024:
            raise ValueError("Workshop subscription list exceeds 1 MiB")
        operator_ids = any(re.match(r"\s*\d+(?:\s|$)", line) for line in path.read_text().splitlines())
    if desired or operator_ids:
        command = [*command, "-workshop", "+sv_workshop_enabled", "1"]
    return command, directory


def _get_container_start_command(server):
    return build_source_container_start_command(server, get_start_command)

do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue

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