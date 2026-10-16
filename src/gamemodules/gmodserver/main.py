"""Garrys Mod-specific lifecycle, configuration, and update helpers."""

import os
from pathlib import Path
import re
import shutil

from gamemodules.gmodserver.gma import extract_gma

from server.modsupport.errors import ModSupportError
from server.modsupport.workshop import validate_workshop_identifier
from server.modsupport.source_addons import build_source_addon_mod_support
from server.modsupport.registry import CuratedRegistryLoader
import utils.steamcmd as steamcmd
from utils.source_console import build_source_container_start_command
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


def load_curated_registry():
    override = os.environ.get("ALPHAGSM_GMOD_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


workshop_app_id = 4000


def download_workshop_addon(path, app_id, item_id, anonymous):
    """Download and safely extract one GMA into an engine-loadable addon tree."""
    item_id = validate_workshop_identifier(item_id)
    payload_root = Path(steamcmd.download_workshop_item(path, app_id, item_id, anonymous))
    payloads = list(payload_root.glob("*.gma"))
    if (payload_root.is_symlink() or len(payloads) != 1
            or not payloads[0].is_file() or payloads[0].is_symlink()):
        raise ModSupportError("Garry's Mod Workshop item must contain one regular GMA addon")
    with payloads[0].open("rb") as handle:
        header = handle.read(5)
    if header != b"GMAD\x03":
        raise ModSupportError("Garry's Mod Workshop item has an invalid GMA signature or version")
    stage_root = Path(path) / "payload"
    if any(parent.is_symlink() for parent in (stage_root, *stage_root.parents)):
        raise ModSupportError("Refusing GMA extraction through symlink paths")
    if stage_root.exists():
        shutil.rmtree(stage_root)
    extract_gma(payloads[0], stage_root / "addons" / item_id)
    return stage_root


def stage_gma_addon(archive_path, stage_root, filename):
    """Stage URL and curated GMAs as the same engine-loadable addon folders."""
    addon_name = re.sub(r"[^a-z0-9_-]+", "-", Path(filename).stem.lower()).strip("-") or "addon"
    extract_gma(archive_path, Path(stage_root) / "addons" / addon_name)


MOD_SUPPORT = build_source_addon_mod_support(
    game_label="Garry's Mod",
    game_dir="garrysmod",
    cache_namespace="gmodserver",
    direct_url_suffixes={".gma": "single"},
    direct_url_filename_description="a .gma addon filename or a supported archive filename",
    curated_registry_loader=load_curated_registry,
    enabled_sources=("url", "gamebanana", "moddb", "workshop"),
    workshop_app_id=workshop_app_id,
    workshop_downloader_getter=lambda: download_workshop_addon,
    single_file_payload_transform_getter=lambda: stage_gma_addon,
    allow_bare_addon_root=True,
    bare_addon_marker_files=("addon.json", "addon.txt"),
    bare_addon_marker_dirs=(
        "lua",
        "materials",
        "models",
        "sound",
        "resource",
        "maps",
        "data",
        "particles",
    ),
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
commands = MODULE.commands + MOD_SUPPORT.commands
command_args = {**MODULE.command_args, **MOD_SUPPORT.command_args}
command_descriptions = {**MODULE.command_descriptions, **MOD_SUPPORT.command_descriptions}
command_functions = {**MODULE.command_functions, **MOD_SUPPORT.command_functions}
max_stop_wait = MODULE.max_stop_wait


def configure(server, ask, port=None, dir=None, *, exe_name=None):
    result = MODULE.configure(server, ask, port, dir, exe_name=exe_name)
    MOD_SUPPORT.ensure_mod_state(server)
    return result


doinstall = MODULE.doinstall


def prestart(server, *args, **kwargs):
    """Apply addon desired state before both process and Docker launches."""
    MODULE.prestart(server, *args, **kwargs)
    if MOD_SUPPORT.ensure_mod_state(server).get("autoapply", True):
        MOD_SUPPORT.apply_configured_mods(server)


restart = MODULE.restart


def get_start_command(server):
    """Enable the engine console explicitly for process and container input."""
    command, directory = MODULE.get_start_command(server)
    return [*command, "-console"], directory


def _get_container_start_command(server):
    """Give the Source engine a terminal while forwarding managed FIFO input."""
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
        tty=True,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}, {'key': 'clientport', 'protocol': 'udp'}, {'key': 'sourcetvport', 'protocol': 'udp'}),
        stdin_open=True,
)
