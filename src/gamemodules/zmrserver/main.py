"""Zombie Master: Reborn-specific lifecycle, configuration, and update helpers."""

import os
import shutil

from server.modsupport.source_addons import (
        build_source_addon_mod_support,
        load_shared_source_curated_registry,
)
from utils.valve_server import define_valve_server_module


import server.runtime as runtime_module
from utils.gamemodules import common as gamemodule_common

# The public app 244310 branch ships a 32-bit srcds that stops during Steam
# startup. previous2021 is the same app's legacy SDK 2013 dedicated branch.
STEAM_BETA_BRANCH = "previous2021"

MODULE = define_valve_server_module(
    game_name='Zombie Master: Reborn',
    engine='source',
    steam_app_id=244310,
    game_dir='zombie_master_reborn',
    executable='srcds_run',
    default_map='zm_docksofthedead',
    max_players=16,
    port=27015,
    client_port=27005,
    sourcetv_port=27020,
    steam_port=None,
    app_id_mod=None,
    config_subdir='cfg',
    config_default='server.cfg',
    default_server_config={'sv_hibernate_when_empty': '0'},
    beta_branch=STEAM_BETA_BRANCH,
)
MOD_SUPPORT = build_source_addon_mod_support(
        game_label='Zombie Master: Reborn',
        game_dir='zombie_master_reborn',
        cache_namespace='zombie_master_reborn',
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


def _assert_required_mod_content(install_dir):
        """Raise when Zombie Master: Reborn content has not been staged locally."""

        required_map = os.path.join(
                install_dir, "zombie_master_reborn", "maps", "zm_docksofthedead.bsp"
        )
        if os.path.isfile(required_map):
                return
        gamemodule_common.raise_byo_requirement(
                "zmrserver",
                "the official Zombie Master: Reborn Beta 6 Linux archive staged under <install_dir>/zombie_master_reborn/",
                actions=(
                        "Download zombie_master_reborn_b6_1.tar.gz, the Linux archive linked from "
                        "https://zombiemaster.dev/",
                        "Extract that complete zombie_master_reborn tree into "
                        "<install_dir>/zombie_master_reborn/ so "
                        "zombie_master_reborn/maps/zm_docksofthedead.bsp exists",
                        "Keep every multiplayer map and resource; the map sentinel does not prove completeness",
                        "Retry setup or start after the Linux archive tree is present locally",
                ),
                docs_slug="zmrserver",
        )


def _alias_dedicated_libraries(install_dir):
        """Copy bin/*_srv.so onto the unsuffixed names srcds_linux loads.

        App 244310 publishes dedicated libraries with a _srv suffix. Extra
        unsuffixed copies survive SteamCMD updates, so a newer or different
        _srv library replaces a stale alias.
        """

        bin_dir = os.path.join(install_dir, "bin")
        if not os.path.isdir(bin_dir):
                return
        for name in os.listdir(bin_dir):
                if not name.endswith("_srv.so"):
                        continue
                source = os.path.join(bin_dir, name)
                if not os.path.isfile(source):
                        continue
                destination = os.path.join(bin_dir, name[:-len("_srv.so")] + ".so")
                if _dedicated_alias_is_current(source, destination):
                        continue
                shutil.copy2(source, destination)


def _dedicated_alias_is_current(source, destination):
        """Return whether the unsuffixed library already matches its _srv source."""

        if not os.path.isfile(destination):
                return False
        source_stat = os.stat(source)
        destination_stat = os.stat(destination)
        if source_stat.st_size != destination_stat.st_size:
                return False
        return source_stat.st_mtime <= destination_stat.st_mtime


def _ensure_linux_executables(server):
        """NTFS installs can omit the execute bit SteamCMD set on Linux files."""

        install_dir = server.data["dir"]
        for relative in ("srcds_run", "srcds_linux"):
                path = os.path.join(install_dir, relative)
                if os.path.isfile(path):
                        os.chmod(path, os.stat(path).st_mode | 0o755)


def install(server):
        """Install the SDK base scaffold, then require staged Zombie Master: Reborn content."""

        MODULE.install(server)
        _alias_dedicated_libraries(server.data["dir"])
        _ensure_linux_executables(server)
        _assert_required_mod_content(server.data["dir"])


doinstall = MODULE.doinstall
update = MODULE.update
restart = MODULE.restart


def prestart(server, *args, **kwargs):
        """Refresh dedicated library aliases, then run the shared Valve prestart."""

        _alias_dedicated_libraries(server.data["dir"])
        _ensure_linux_executables(server)
        MODULE.sync_server_config(server)
        return MODULE.prestart(server, *args, **kwargs)


def get_start_command(server):
        """Build the start command after validating staged Zombie Master: Reborn content."""

        _assert_required_mod_content(server.data["dir"])
        return MODULE.get_start_command(server)


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


def get_asset_requirements(server):
    """Describe this game's owned files, acquisition routes and staging limits."""
    from utils.byo_files import load_requirements
    return load_requirements(server, __file__, 'byo_assets.json')
