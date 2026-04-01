"""Left 4 Dead-specific lifecycle, configuration, and update helpers."""

from utils.valve_server import define_valve_server_module


MODULE = define_valve_server_module(
    game_name='Left 4 Dead',
    engine='source',
    steam_app_id=222840,
    game_dir='left4dead',
    executable='srcds_run',
    default_map='l4d_hospital01_apartment',
    max_players=8,
    port=27015,
    client_port=27005,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
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
