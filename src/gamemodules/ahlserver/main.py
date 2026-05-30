"""Action Half-Life-specific lifecycle, configuration, and update helpers."""

import os

from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Action Half-Life',
    engine='goldsrc',
    steam_app_id=90,
    game_dir='action',
    executable='hlds_run',
    default_map='ahl_hydro',
    max_players=16,
    port=27015,
    client_port=27005,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod='cstrike',
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
doinstall = MODULE.doinstall
prestart = MODULE.prestart
update = MODULE.update
restart = MODULE.restart
do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue


def _assert_required_mod_content(install_dir):
    """Raise when the Action Half-Life mod payload has not been staged locally."""

    required_map = os.path.join(install_dir, "action", "maps", "ahl_hydro.bsp")
    if os.path.isfile(required_map):
        return
    gamemodule_common.raise_byo_requirement(
        "ahlserver",
        "an owned Action Half-Life mod content tree",
        actions=(
            "Copy the complete Action Half-Life mod tree into <install_dir>/action/",
            "Make sure <install_dir>/action/maps/ahl_hydro.bsp exists after staging the content",
            "Retry setup or start once the staged mod files are present locally",
        ),
        docs_slug="ahlserver",
    )


def install(server):
    """Install the HLDS base files, then require staged Action Half-Life content."""

    MODULE.install(server)
    _assert_required_mod_content(server.data["dir"])


def get_start_command(server):
    """Build the start command after validating Action Half-Life content."""

    _assert_required_mod_content(server.data["dir"])
    return MODULE.get_start_command(server)

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
