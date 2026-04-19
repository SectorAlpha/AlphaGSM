"""Garrys Mod-specific lifecycle, configuration, and update helpers."""

import os
import re

import utils.steamcmd as steamcmd
from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Garrys Mod',
    engine='source',
    steam_app_id=4020,
    game_dir='garrysmod',
    executable='srcds_run',
    default_map='gm_construct',
    max_players=16,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
)

_GMOD_CONTENT_INSTALLS = (
    ("cstrike", 232330, "cstrike"),
    ("hl2mp", 232370, "hl2mp"),
    ("tf", 232250, "tf"),
)
_GMOD_MOUNTDEPOTS_DEFAULTS = (
    "cstrike",
    "hl1",
    "hl1_hd",
    "hl2",
    "hl2mp",
    "episodic",
    "ep2",
    "lostcoast",
)
_GMOD_KEYVALUE_ENTRY_RE = re.compile(r'^\s*"(?P<key>[^"]+)"\s*"(?P<value>[^"]*)"\s*$')


def _gmod_cfg_dir(server):
    return os.path.join(server.data["dir"], "garrysmod", "cfg")


def _gmod_content_root(server):
    return os.path.join(server.data["dir"], "_gmod_content")


def _read_keyvalue_mapping(path):
    mapping = {}
    if not os.path.isfile(path):
        return mapping
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = _GMOD_KEYVALUE_ENTRY_RE.match(line)
            if match is not None:
                mapping[match.group("key")] = match.group("value")
    return mapping


def _write_keyvalue_mapping(path, root_name, mapping):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write('"{}"\n'.format(root_name))
        handle.write("{\n")
        for key in sorted(mapping):
            handle.write('\t"{}"\t\t"{}"\n'.format(key, mapping[key]))
        handle.write("}\n")


def _gmod_mount_paths(server):
    content_root = _gmod_content_root(server)
    return {
        mount_key: os.path.join(content_root, mount_key, game_dir)
        for mount_key, _app_id, game_dir in _GMOD_CONTENT_INSTALLS
    }


def _install_supporting_source_content(server, validate=False):
    for mount_key, app_id, _game_dir in _GMOD_CONTENT_INSTALLS:
        steamcmd.download(
            os.path.join(_gmod_content_root(server), mount_key),
            app_id,
            True,
            validate=validate,
        )


def _ensure_mount_configs(server):
    cfg_dir = _gmod_cfg_dir(server)
    os.makedirs(cfg_dir, exist_ok=True)

    mount_cfg_path = os.path.join(cfg_dir, "mount.cfg")
    mount_cfg = _read_keyvalue_mapping(mount_cfg_path)
    mount_cfg.update(_gmod_mount_paths(server))
    _write_keyvalue_mapping(mount_cfg_path, "mountcfg", mount_cfg)

    mountdepots_path = os.path.join(cfg_dir, "mountdepots.txt")
    mountdepots = _read_keyvalue_mapping(mountdepots_path)
    for depot in _GMOD_MOUNTDEPOTS_DEFAULTS:
        mountdepots.setdefault(depot, "1")
    _write_keyvalue_mapping(mountdepots_path, "gamedepotsystem", mountdepots)


def install(server):
    """Install Garry's Mod and common mountable Source content."""

    MODULE.install(server)
    _install_supporting_source_content(server, validate=False)
    _ensure_mount_configs(server)


def update(server, validate=False, restart=False):
    """Update Garry's Mod and common mountable Source content."""

    MODULE.update(server, validate=validate, restart=False)
    _install_supporting_source_content(server, validate=validate)
    _ensure_mount_configs(server)
    if restart:
        print("Starting the server up")
        server.start()

steam_app_id = MODULE.steam_app_id
commands = MODULE.commands
command_args = MODULE.command_args
command_descriptions = MODULE.command_descriptions
command_functions = MODULE.command_functions
max_stop_wait = MODULE.max_stop_wait
configure = MODULE.configure
doinstall = MODULE.doinstall
prestart = MODULE.prestart
restart = MODULE.restart
get_start_command = MODULE.get_start_command
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
