"""Left 4 Dead 2-specific lifecycle, configuration, and update helpers."""

import os
from pathlib import Path
import subprocess as sp

from server.modsupport.source_addons import build_source_addon_mod_support
from server.modsupport.registry import CuratedRegistryLoader
import utils.steamcmd as steamcmd
from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

MODULE = define_valve_server_module(
    game_name='Left 4 Dead 2',
    engine='source',
    steam_app_id=222860,
    game_dir='left4dead2',
    executable='srcds_run',
    default_map='c5m1_waterfront',
    max_players=8,
    port=27015,
    client_port=27005,
    sourcetv_port=None,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
    enable_map_validation=True,
)


def load_curated_registry():
    override = os.environ.get("ALPHAGSM_L4D2_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_mods.json")
    return CuratedRegistryLoader.load(path)


MOD_SUPPORT = build_source_addon_mod_support(
    game_label="Left 4 Dead 2",
    game_dir="left4dead2",
    cache_namespace="left4dead2",
    direct_url_suffixes={".vpk": "single"},
    direct_url_filename_description="a .vpk addon filename or a supported archive filename",
    curated_registry_loader=load_curated_registry,
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


def _finalize_source_install(server):
    """Apply the standard Valve Source install cleanup after SteamCMD."""

    if os.path.isfile(os.path.join(server.data["dir"], "srcds_run_64")):
        server.data["exe_name"] = "srcds_run_64"

    for script_name in ("srcds_run", "srcds_run.sh", os.path.join("bin", "srcds_run.sh")):
        script_path = os.path.join(server.data["dir"], script_name)
        if not os.path.isfile(script_path):
            continue
        with open(script_path, "rb") as handle:
            content = handle.read()
        if content.startswith(b"#!") and b"\r\n" in content:
            with open(script_path, "wb") as handle:
                handle.write(content.replace(b"\r\n", b"\n"))


def _raise_auth_install_requirement():
    gamemodule_common.raise_auth_requirement(
        "l4d2server",
        "authenticated Steam or SteamCMD access to install the Left 4 Dead 2 dedicated server depots",
        actions=(
            "Authenticate Steam or SteamCMD with an account that is entitled to Left 4 Dead 2 before retrying setup",
            "Re-run setup after the future AlphaGSM SteamCMD auth-profile flow is configured for this host",
        ),
        docs_slug="l4d2server",
    )


def _translate_auth_install_failure(exc):
    output = str(getattr(exc, "output", "") or "")
    if "Failed to install app '222860' (Invalid platform)" in output:
        _raise_auth_install_requirement()
    raise exc


_base_doinstall = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=True,
    download_kwargs={"force_platform": "linux"},
)
_base_install = gamemodule_common.make_steamcmd_install_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=True,
    sync_server_config=MODULE.sync_server_config,
    post_download_hook=_finalize_source_install,
    download_kwargs={"force_platform": "linux"},
)
_base_update = gamemodule_common.make_steamcmd_update_hook(
    steamcmd_module=steamcmd,
    steam_app_id=steam_app_id,
    steam_anonymous_login_possible=True,
    sync_server_config=MODULE.sync_server_config,
    post_download_hook=_finalize_source_install,
    download_kwargs={"force_platform": "linux"},
)


def doinstall(server):
    try:
        _base_doinstall(server)
    except sp.CalledProcessError as exc:
        _translate_auth_install_failure(exc)


def install(server):
    try:
        _base_install(server)
    except sp.CalledProcessError as exc:
        _translate_auth_install_failure(exc)


prestart = MODULE.prestart


def update(server, validate=False, restart=False):
    try:
        _base_update(server, validate=validate, restart=restart)
    except sp.CalledProcessError as exc:
        _translate_auth_install_failure(exc)


restart = MODULE.restart
get_start_command = MODULE.get_start_command


do_stop = MODULE.do_stop
status = MODULE.status
message = MODULE.message
backup = MODULE.backup
checkvalue = MODULE.checkvalue

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
