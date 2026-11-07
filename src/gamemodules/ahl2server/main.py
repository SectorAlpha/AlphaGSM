"""Action: Source-specific lifecycle, configuration, and update helpers."""

from server.modsupport.source_addons import (
        build_source_addon_mod_support,
        load_shared_source_curated_registry,
)
from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Action: Source',
    engine='source',
    steam_app_id=985050,
    game_dir='ahl2',
    executable='srcds_run',
    default_map='act_airport',
    max_players=20,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    runtime_app_id=985050,
    config_subdir='cfg',
    config_default='server.cfg',
)
MOD_SUPPORT = build_source_addon_mod_support(
        game_label='Action: Source',
        game_dir='ahl2',
        cache_namespace='ahl2',
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


install = MODULE.install
doinstall = MODULE.doinstall
prestart = MODULE.prestart
update = MODULE.update
restart = MODULE.restart


def get_start_command(server):
    """Build AHL2's Steam-installed Source console launch command."""

    command, working_dir = MODULE.get_start_command(server)
    return [command[0], "-console", "-steam", *command[1:]], working_dir


def get_query_address(server):
    """Return Action: Source's live TCP health endpoint.

    The current Linux payload does not implement the configured Source
    hibernation cvar and does not answer A2S while empty. It does expose
    the managed game port over TCP, which is the same endpoint for both
    process and Docker runtimes.
    """

    return (
        runtime_module.resolve_query_host(server),
        int(server.data["port"]),
        "tcp",
    )


get_info_address = get_query_address

do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
        extra={'run_as_host_user': True, 'container_home': '/home/alphagsm'},
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
        stdin_open=True,
        extra={'run_as_host_user': True, 'container_home': '/home/alphagsm'},
)
