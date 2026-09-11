"""Double Action: Boogaloo-specific lifecycle, configuration, and update helpers."""

import os

from server.modsupport.source_addons import (
        build_source_addon_mod_support,
        load_shared_source_curated_registry,
)
from utils.valve_server import define_valve_server_module, legacy_source_docker_mounts


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Double Action: Boogaloo',
    engine='source',
    steam_app_id=317800,
    game_dir='dab',
    executable='dabds.sh',
    default_map='da_rooftops',
    max_players=10,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    runtime_app_id=317360,
    config_subdir='cfg',
    config_default='server.cfg',
)
MOD_SUPPORT = build_source_addon_mod_support(
        game_label='Double Action: Boogaloo',
        game_dir='dab',
        cache_namespace='dab',
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
restart = MODULE.restart
get_start_command = MODULE.get_start_command
do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue


def _has_current_double_action_content(server):
        """Return whether the current Double Action content tree is already staged."""

        gameinfo_path = os.path.join(server.data["dir"], "dab", "GameInfo.txt")
        launcher_path = os.path.join(server.data["dir"], "dabds.sh")
        return os.path.isfile(gameinfo_path) and os.path.isfile(launcher_path)


def _require_current_double_action_content(server):
        """Fail fast unless the current entitled Double Action content is present."""

        if _has_current_double_action_content(server):
                return
        gamemodule_common.raise_auth_requirement(
                "dabserver",
                "authenticated Steam or SteamCMD access to the current Double Action: Boogaloo game content, because the retired dedicated tool app 317800 still crashes on modern Linux and the current app 317360 rejects anonymous SteamCMD with No subscription",
                actions=(
                        "Authenticate Steam or SteamCMD with an account entitled to Double Action: Boogaloo so the current app 317360 content can be staged before setup/start",
                        "Or stage a full current Double Action content tree containing dab/GameInfo.txt and the Linux Source SDK 2013 multiplayer server files under <install_dir>/ before setup/start",
                ),
                docs_slug="dabserver",
        )


def install(server):
        _require_current_double_action_content(server)
        MODULE.sync_server_config(server)


def prestart(server, *args, **kwargs):
        _require_current_double_action_content(server)
        return MODULE.prestart(server, *args, **kwargs)


def update(server, validate=False, restart=False):
        gamemodule_common.raise_auth_requirement(
                "dabserver",
                "authenticated Steam or SteamCMD access to refresh the current Double Action: Boogaloo content outside the retired anonymous dedicated tool lane",
                actions=(
                        "Refresh the current app 317360 content with authenticated Steam or SteamCMD and then rerun start",
                ),
                docs_slug="dabserver",
        )

get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        mounts=legacy_source_docker_mounts,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        mounts=legacy_source_docker_mounts,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
        stdin_open=True,
)
