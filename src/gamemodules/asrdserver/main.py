"""Anonymous Reactive Drop dedicated server through native Windows/Wine runtime."""

import ipaddress
from pathlib import Path

import server.runtime as runtime_module
from server import ServerError
from server.settable_keys import SettingSpec
from server.modsupport.native_workshop import build_native_workshop_support, safe_server_path
from utils.gamemodules import common as gamemodule_common
import utils.proton as proton
import utils.steamcmd as steamcmd
from utils.simple_kv_config import rewrite_space_config
from utils.valve_server import define_valve_server_module
from .workshop import WORKSHOP_APP_ID, apply_workshop

steam_app_id = 563560
steam_anonymous_login_possible = True
workshop_app_id = WORKSHOP_APP_ID
process_platforms = ('linux',)
MODULE = define_valve_server_module(
    game_name='Alien Swarm: Reactive Drop', engine='source', steam_app_id=steam_app_id,
    game_dir='reactivedrop', executable='srcds_console.exe', default_map='lobby',
    max_players=12, port=27015, client_port=27005, sourcetv_port=27020,
    steam_port=None, app_id_mod=None, config_subdir='cfg', config_default='server.cfg',
)
MOD_SUPPORT = build_native_workshop_support(
    game_label='Reactive Drop', workshop_app_id=workshop_app_id, apply_callback=apply_workshop,
)
commands = MODULE.commands + MOD_SUPPORT.commands
command_args = {**MODULE.command_args, **MOD_SUPPORT.command_args}
command_descriptions = {**MODULE.command_descriptions, **MOD_SUPPORT.command_descriptions}
command_functions = {**MODULE.command_functions, **MOD_SUPPORT.command_functions}
max_stop_wait = MODULE.max_stop_wait
config_sync_keys = MODULE.config_sync_keys
setting_schema = {**MODULE.setting_schema, 'bindaddress': SettingSpec(
    canonical_key='bindaddress', description='Local IPv4 interface to bind, or 0.0.0.0 for all interfaces.',
    apply_to=('datastore', 'launch_args'), launch_arg_tokens=('-ip',),
)}


def configure(server, ask, port=None, dir=None, *, exe_name='srcds_console.exe'):
    result = MODULE.configure(server, ask, port, dir, exe_name=exe_name)
    server.data.setdefault('wineprefix', str(Path(server.data['dir']) / '.wine'))
    MOD_SUPPORT.ensure_mod_state(server)
    return result


def doinstall(server, *, validate=True):
    """Download the upstream-recommended game and server SDK depots together."""
    for app_id in (1007, steam_app_id):
        steamcmd.download(server.data['dir'], app_id, True, validate=validate, force_windows=True)


def sync_server_config(server):
    configured = Path(str(server.data.get('server_cfg', 'server.cfg')))
    if configured.is_absolute() or '\\' in str(configured) or '\x00' in str(configured):
        raise ServerError('Server config must be a contained relative filename')
    path = safe_server_path(server, (Path('reactivedrop/cfg') / configured).as_posix())
    path.parent.mkdir(parents=True, exist_ok=True)
    MODULE.sync_server_config(server)
    rewrite_space_config(path,
                         {'rd_server_shutdown_when_empty': '0', 'sv_hibernate_when_empty': '0'})


def _apply_automatic(server):
    if MOD_SUPPORT.ensure_mod_state(server).get('autoapply', True):
        MOD_SUPPORT.apply_configured_mods(server)


def install(server):
    doinstall(server)
    sync_server_config(server)
    _apply_automatic(server)


def prestart(server):
    sync_server_config(server)
    _apply_automatic(server)


def update(server, validate=True, restart=False):
    running = server.isrunning()
    if running:
        server.stop()
    doinstall(server, validate=validate)
    sync_server_config(server)
    _apply_automatic(server)
    if restart and running:
        server.start()


restart = gamemodule_common.make_restart_hook()


def get_start_command(server):
    command, directory = MODULE.get_start_command(server)
    # Windows Source initializes sockets before + commands and needs an explicit config exec.
    command[command.index('+ip')] = '-ip'
    command[command.index('-ip') + 1] = str(server.data.get('bindaddress', '0.0.0.0'))
    map_index = command.index('+map')
    command[map_index:map_index] = ['+exec', str(server.data['server_cfg'])]
    command.extend(['-console', '-condebug'])
    return proton.wrap_command(command, wineprefix=server.data.get('wineprefix')), directory


do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
def checkvalue(server, key, *value):
    tokens = (key,) if isinstance(key, str) else key
    if tokens and tokens[0] == 'bindaddress':
        if len(tokens) != 1 or len(value) != 1:
            raise ServerError('bindaddress requires one local IPv4 address')
        try:
            return str(ipaddress.IPv4Address(value[0]))
        except ipaddress.AddressValueError as exc:
            raise ServerError('bindaddress requires a local IPv4 address') from exc
    return MODULE.checkvalue(server, tokens, *value)


get_query_address = MODULE.get_query_address
get_info_address = MODULE.get_info_address
_PORTS = ({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'},
          {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'})
get_runtime_requirements = gamemodule_common.make_proton_runtime_requirements_builder(
    port_definitions=_PORTS, stdin_open=True, stop_mode='docker-stop',
)
# Wine requires terminal-backed stdin for the native Win32 console input APIs.
# Keep docker-stop: exec-console would replace that terminal input with a FIFO.
get_container_spec = gamemodule_common.make_proton_container_spec_builder(
    get_start_command=get_start_command, port_definitions=_PORTS, stdin_open=True,
    tty=True, stop_mode='docker-stop',
)
command_functions.update({'update': update, 'restart': restart})
