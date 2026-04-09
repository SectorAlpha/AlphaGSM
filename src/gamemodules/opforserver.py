"""Opposing Force-specific lifecycle, configuration, and update helpers."""

from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module

MODULE = define_valve_server_module(
    game_name='Opposing Force',
    engine='goldsrc',
    steam_app_id=90,
    game_dir='gearbox',
    executable='hlds_run',
    default_map='op4_bootcamp',
    max_players=16,
    port=27015,
    client_port=27005,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod='gearbox',
    config_subdir='',
    config_default='server.cfg',
)

steam_app_id = MODULE.steam_app_id
commands = MODULE.commands
command_args = MODULE.command_args
command_descriptions = MODULE.command_descriptions
command_functions = MODULE.command_functions
max_stop_wait = MODULE.max_stop_wait
configure = MODULE.configure
install = MODULE.install
doinstall = MODULE.doinstall
prestart = MODULE.prestart
update = MODULE.update
restart = MODULE.restart
get_start_command = MODULE.get_start_command
do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue

def get_runtime_requirements(server):
    return runtime_module.build_runtime_requirements(
        server,
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}),
    )

def get_container_spec(server):
    return runtime_module.build_container_spec(
        server,
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}),
        stdin_open=True,
    )
