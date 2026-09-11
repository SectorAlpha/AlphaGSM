"""Nuclear Dawn-specific lifecycle, configuration, and update helpers."""

import os

from server.modsupport.source_addons import (
        build_source_addon_mod_support,
        load_shared_source_curated_registry,
)
from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Nuclear Dawn',
    engine='source',
    steam_app_id=111710,
    game_dir='nucleardawn',
    executable='srcds_run',
    default_map='hydro',
    max_players=32,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
)
MOD_SUPPORT = build_source_addon_mod_support(
        game_label='Nuclear Dawn',
        game_dir='nucleardawn',
        cache_namespace='nucleardawn',
        direct_url_suffixes={},
        direct_url_filename_description='a supported archive filename',
        curated_registry_loader=load_shared_source_curated_registry,
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


def _assert_required_mod_content(install_dir):
        """Raise when Nuclear Dawn content has not been staged locally."""

        required_map = os.path.join(install_dir, "nucleardawn", "maps", "hydro.bsp")
        if os.path.isfile(required_map):
                return
        gamemodule_common.raise_byo_requirement(
                "ndserver",
                "a staged Nuclear Dawn content tree",
                actions=(
                        "Copy the complete Nuclear Dawn content tree into <install_dir>/nucleardawn/",
                        "Make sure <install_dir>/nucleardawn/maps/hydro.bsp exists after staging the game files",
                        "Retry setup or start once the staged content is present locally",
                ),
                docs_slug="ndserver",
        )


def install(server):
        """Install the dedicated scaffold, then require staged Nuclear Dawn content."""

        MODULE.install(server)
        _assert_required_mod_content(server.data["dir"])


doinstall = MODULE.doinstall
prestart = MODULE.prestart
update = MODULE.update
restart = MODULE.restart


def get_start_command(server):
        """Build the start command after validating staged Nuclear Dawn content."""

        _assert_required_mod_content(server.data["dir"])
        return MODULE.get_start_command(server)


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
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
        stdin_open=True,
)
