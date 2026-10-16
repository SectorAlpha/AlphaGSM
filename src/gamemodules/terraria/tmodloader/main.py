"""Unattended tModLoader dedicated servers from official public releases."""

import os
from pathlib import Path
import re

import downloader
import server.runtime as runtime_module
from server.errors import ServerError
from server.modsupport.native_workshop import build_native_workshop_support, safe_server_path, write_managed_text
from utils import archive_install, github_releases
from utils.gamemodules import common as gamemodule_common
from utils.gamemodules.terraria import common
from .workshop import apply_workshop_mods

module_contract_version = 1
steam_app_id = 1281930
workshop_app_id = 1281930
steam_anonymous_login_possible = True
max_stop_wait = 1
config_sync_keys = ('port', 'maxplayers', 'world', 'worldname', 'worldsize', 'serverpassword')
setting_schema = common.setting_schema
backup = common.backup
do_stop = common.do_stop
message = common.message
status = common.status
get_wipe_paths = common.get_wipe_paths
commands = ('update', 'restart', 'mod')
command_args = common.command_args.copy()
command_args.update(gamemodule_common.build_setup_update_restart_command_args(
    'The game port', 'The tModLoader installation directory'))
# Retain the family release/version options and explicit world-creation option.
command_args['setup'] = common.command_args['setup']
command_descriptions = gamemodule_common.build_update_restart_command_descriptions(
    'Update the selected official tModLoader release.', 'Restart the tModLoader server.')
command_functions = {}
restart = gamemodule_common.make_restart_hook()
MOD_SUPPORT = build_native_workshop_support(
    game_label='tModLoader', workshop_app_id=workshop_app_id, apply_callback=apply_workshop_mods)
command_args.update(MOD_SUPPORT.command_args)
command_descriptions.update(MOD_SUPPORT.command_descriptions)
command_functions.update(MOD_SUPPORT.command_functions)
ensure_mod_state = MOD_SUPPORT.ensure_mod_state
apply_configured_mods = MOD_SUPPORT.apply_configured_mods
cleanup_configured_mods = MOD_SUPPORT.cleanup_configured_mods


def resolve_tmodloader_download(version=None):
    """Select the named server asset from an official stable or pinned release."""
    return github_releases.resolve_release_asset(
        'https://api.github.com/repos/tModLoader/tModLoader/releases/latest',
        lambda asset: asset.get('name') == 'tModLoader.zip', version=version)


def configure(server, ask, port=None, dir=None, *, version=None, url=None,
              exe_name='start-tModLoaderServer.sh', download_name='tmodloader.zip'):
    """Configure a public-release installation without Steam client credentials."""
    if url is not None:
        raise ServerError('tModLoader setup uses official GitHub release assets; select --version')
    selected_version, selected_url = resolve_tmodloader_download(version)
    result = common.configure_base(
        server, ask, port, dir, exe_name=exe_name, version=selected_version,
        url=selected_url, download_name=download_name, world_name=server.name,
        world_size=1, backupfiles=('Worlds', 'Saved', 'Mods', 'serverconfig.txt'))
    server.data['release'] = version or 'latest'
    gamemodule_common.set_steam_install_metadata(
        server, steam_app_id=steam_app_id, steam_anonymous_login_possible=True)
    ensure_mod_state(server)
    server.data.save()
    return result


def _world(server):
    value = str(server.data.get('world', server.name + '.wld'))
    if not re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,100}\.wld', value):
        raise ServerError('World must be a contained .wld filename without spaces')
    return 'Worlds/' + value


def sync_server_config(server):
    """Update declared Terraria config keys while retaining operator settings."""
    if not server.data.get('dir'):
        return
    path = safe_server_path(server, 'serverconfig.txt')
    lines = path.read_text(encoding='utf-8').splitlines() if path.exists() else []
    values = {
        'port': str(server.data.get('port', 7777)),
        'maxplayers': str(server.data.get('maxplayers', 8)),
        'world': _world(server), 'worldpath': 'Worlds',
        'worldname': str(server.data.get('worldname', server.name)),
        'password': str(server.data.get('serverpassword', '')),
        'modpath': 'Mods', 'upnp': '0',
    }
    if any('\n' in value or '\r' in value for value in values.values()):
        raise ServerError('Server configuration values must be single-line')
    retained = [line for line in lines if line.partition('=')[0].strip().lower() not in values]
    write_managed_text(server, 'serverconfig.txt', '\n'.join(
        retained + [key + '=' + value for key, value in values.items()]) + '\n')


def install(server):
    """Install release code while preserving the operator's server configuration."""
    root = Path(server.data['dir'])
    root.mkdir(parents=True, exist_ok=True)
    if server.data.get('current_url') != server.data['url'] or not (root / server.data['exe_name']).is_file():
        downloaded = downloader.getpath('url', (
            server.data['url'], server.data['download_name'], 'zip'))
        source = archive_install.resolve_archive_root(
            downloaded, archive_name=server.data['download_name'])
        archive_install.sync_tree(source, root, skip_root_files=(
            server.data['download_name'], 'serverconfig.txt'))
        server.data['current_url'] = server.data['url']
    archive_install.ensure_executable(root / server.data['exe_name'])
    sync_server_config(server)
    ensure_mod_state(server)
    if server.data['mods']['desired']['workshop'] and server.data['mods'].get('autoapply', True):
        apply_configured_mods(server)
    server.data.save()


def update(server, validate=False, restart=False):
    """Refresh the selected release without silently moving pinned installations."""
    del validate
    server.stop()
    server.data['version'], server.data['url'] = resolve_tmodloader_download(
        server.data.get('release', 'latest'))
    install(server)
    if restart:
        server.start()


def prestart(server, *, autocreate=False):
    """Refresh configuration and apply enabled desired mods before launch."""
    del autocreate
    sync_server_config(server)
    mods = ensure_mod_state(server)
    if mods.get('autoapply', True) and (mods['desired']['workshop'] or mods.get('tmodloader_owned_names')):
        apply_configured_mods(server)


def get_start_command(server, *, autocreate=False):
    """Use the upstream no-Steam server launcher with contained save directories."""
    script = safe_server_path(server, server.data.get('exe_name', 'start-tModLoaderServer.sh'))
    if not script.is_file():
        raise ServerError('Run setup to install the tModLoader server launcher')
    command = ['bash', script.relative_to(Path(server.data['dir']).resolve()).as_posix(),
               '-nosteam', '-config', 'serverconfig.txt', '-tmlsavedirectory', 'Saved']
    if autocreate and not safe_server_path(server, _world(server)).exists():
        command.extend(['-autocreate', str(server.data.get('worldsize', 1))])
    return command, server.data['dir']


def checkvalue(server, key, *value):
    """Validate native settings, including the contained world filename."""
    if key and key[0] == 'world':
        if not value:
            raise ServerError('Specify a world filename')
        proxy = type('WorldConfig', (), {'name': server.name, 'data': {'world': str(value[0])}})()
        _world(proxy)
        return str(value[0])
    result = common.checkvalue(server, key, *value)
    if key and key[0] in ('worldname', 'serverpassword') and ('\n' in str(result) or '\r' in str(result)):
        raise ServerError('Configuration values must be single-line')
    if key and key[0] in ('port', 'maxplayers', 'worldsize'):
        limits = {'port': (1, 65535), 'maxplayers': (1, 255), 'worldsize': (1, 3)}
        lower, upper = limits[key[0]]
        if not lower <= int(result) <= upper:
            raise ServerError(f'{key[0]} must be between {lower} and {upper}')
    return result


def get_query_address(server):
    """Use the framed native Terraria handshake rather than an empty TCP probe."""
    return runtime_module.resolve_query_host(server), int(server.data['port']), 'terraria'


get_info_address = get_query_address
get_runtime_requirements = gamemodule_common.make_runtime_requirements_builder(
    family='steamcmd-linux', port_definitions=({'key': 'port', 'protocol': 'tcp'},),
    extra={'host_dependencies': ({'id': 'bash', 'display_name': 'Bash', 'command': 'bash'},)})


def get_container_spec(server, *, autocreate=False):
    """Publish the same launch contract using the branch's Linux runtime image."""
    return runtime_module.build_container_spec(
        server, family='steamcmd-linux',
        get_start_command=lambda current: get_start_command(current, autocreate=autocreate),
        port_definitions=({'key': 'port', 'protocol': 'tcp'},), stdin_open=True)
