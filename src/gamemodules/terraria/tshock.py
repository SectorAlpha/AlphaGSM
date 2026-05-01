"""TShock server module for Terraria."""

import os
from pathlib import Path

import server.runtime as runtime_module
from server import ServerError
from server.modsupport.downloads import download_to_cache
from server.modsupport.plugin_jars import build_plugin_jar_mod_support
from server.modsupport.providers import resolve_direct_url_entry, resolve_moddb_entry
from server.modsupport.registry import CuratedRegistryLoader

from .common import (
    backup,
    checkvalue,
    command_args,
    command_descriptions,
    command_functions,
    commands,
    configure_base,
    do_stop,
    get_tshock_start_command,
    install_archive,
    message,
    resolve_tshock_download,
    setting_schema,
    status,
)
from utils.gamemodules import common as gamemodule_common


commands = commands + ("mod",)
command_args = command_args.copy()
command_descriptions = command_descriptions.copy()
command_functions = command_functions.copy()

TSHOCK_MOD_CACHE_DIRNAME = "terraria-tshock"


def load_tshock_curated_registry(server=None):
    """Load the checked-in TShock plugin registry or an override file."""

    del server
    override = os.environ.get("ALPHAGSM_TSHOCK_CURATED_MODS_PATH")
    path = Path(override) if override else Path(__file__).with_name("curated_plugins.json")
    return CuratedRegistryLoader.load(path)
MOD_SUPPORT = build_plugin_jar_mod_support(
    game_label="TShock",
    curated_registry_loader=load_tshock_curated_registry,
    cache_namespace=TSHOCK_MOD_CACHE_DIRNAME,
    download_to_cache_getter=lambda: download_to_cache,
    resolve_direct_url_entry_getter=lambda: resolve_direct_url_entry,
    resolve_moddb_entry_getter=lambda: resolve_moddb_entry,
    allowed_destinations=("ServerPlugins", "tshock"),
    direct_url_suffixes={".dll": "dll", ".zip": "zip"},
    direct_url_filename_description="a plugin .dll or .zip filename",
    direct_url_requirement_description="a plugin URL",
    source_identifier_description="plugin family, URL, or Mod DB page URL",
    single_file_destinations={"dll": "ServerPlugins"},
    bare_archive_destination="ServerPlugins",
    bare_archive_file_suffixes=(".dll", ".deps.json", ".pdb", ".xml"),
)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions.update(MOD_SUPPORT.command_functions)
ensure_mod_state = MOD_SUPPORT.ensure_mod_state
apply_configured_mods = MOD_SUPPORT.apply_configured_mods
cleanup_configured_mods = MOD_SUPPORT.cleanup_configured_mods
tshock_mod_command = MOD_SUPPORT.command_functions["mod"]


def configure(
    server,
    ask,
    port=None,
    dir=None,
    *,
    version=None,
    url=None,
    exe_name="TShock.Server.dll",
    download_name="tshock.zip"
):
    """Collect and store configuration values for a TShock server."""

    if url is None:
        version, url = resolve_tshock_download()
    result = configure_base(
        server,
        ask,
        port,
        dir,
        exe_name=exe_name,
        version=version,
        url=url,
        download_name=download_name,
        max_players=8,
        world_name=server.name,
        world_size=2,
        backupfiles=("Worlds", "serverconfig.txt", "tshock"),
        java_runtime="dotnet",
    )
    ensure_mod_state(server)
    return result


def install(server):
    """Download and install the TShock server files."""

    install_archive(server)
    ensure_mod_state(server)
    if server.data["mods"]["enabled"] and server.data["mods"]["autoapply"]:
        apply_configured_mods(server)


def get_start_command(server):
    """Build the start command for TShock."""

    return get_tshock_start_command(server)


get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
        family='steamcmd-linux',
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
)

get_container_spec = gamemodule_common.make_container_spec_builder(
        family='steamcmd-linux',
        get_start_command=get_start_command,
        port_definitions=({'key': 'port', 'protocol': 'udp'}, {'key': 'port', 'protocol': 'tcp'}),
        stdin_open=True,
)
