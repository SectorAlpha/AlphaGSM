"""Base Defense-specific lifecycle, configuration, and update helpers."""

from utils.valve_server import define_valve_server_module


MODULE = define_valve_server_module(
    game_name='Base Defense',
    engine='goldsrc',
    steam_app_id=817300,
    game_dir='bdef',
    executable='hlds_run',
    default_map='pve_tomb',
    max_players=3,
    port=27015,
    client_port=27005,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod=None,
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
