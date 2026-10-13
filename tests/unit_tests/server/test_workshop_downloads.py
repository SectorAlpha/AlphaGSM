"""Shared anonymous Workshop downloads across SteamCMD server modules."""

from pathlib import Path
from importlib import import_module
import subprocess
from types import SimpleNamespace

import pytest

from server import ServerError
from server.modsupport import workshop
from server.modsupport import workshop_downloads as downloads
from server.server import Server
from server.module_catalog import load_default_module_catalog


class Data(dict):
    def save(self):
        pass


def server(tmp_path, **module_fields):
    root = tmp_path / 'server'
    root.mkdir()
    (root / 'steam_appid.txt').write_text('550\n')
    return SimpleNamespace(module=SimpleNamespace(steam_app_id=222860,
        steam_anonymous_login_possible=True, **module_fields), data=Data(dir=str(root)))


@pytest.fixture
def payload(tmp_path, monkeypatch):
    content = tmp_path / 'steam-content'
    content.mkdir()
    (content / 'addon.vpk').write_bytes(b'addon')
    calls = []
    monkeypatch.setattr(downloads.steamcmd, 'download_workshop_item', lambda path, app, item, anonymous:
        calls.append((app, item, anonymous)) or str(content))
    monkeypatch.setattr(workshop, 'resolve_workshop_item', lambda item, app:
        {'workshop_id': workshop.normalize_workshop_identifier(item)})
    monkeypatch.setattr(workshop, 'resolve_workshop_collection', lambda item, app: ['10', '11'])
    return calls


def test_download_item_url_uses_installed_game_identity_and_anonymous_login(tmp_path, payload):
    instance = server(tmp_path)
    downloads.run_workshop_command(instance, 'download', 'item',
        'https://steamcommunity.com/sharedfiles/filedetails/?id=10')
    assert payload == [(550, '10', True)]
    target = Path(instance.data['dir']) / '.alphagsm/workshop/content/550/10/addon.vpk'
    assert target.read_bytes() == b'addon'
    assert not (Path(instance.data['dir']) / 'left4dead2/addons').exists()
    assert instance.data['workshop_downloads']['items'][0]['workshop_id'] == '10'


def test_download_collection_url_validates_before_all_downloads(tmp_path, payload):
    instance = server(tmp_path)
    downloads.run_workshop_command(instance, 'download', 'collection',
        'https://steamcommunity.com/sharedfiles/filedetails/?id=1')
    assert payload == [(550, '10', True), (550, '11', True)]
    assert len(instance.data['workshop_downloads']['items']) == 2


def test_missing_identity_fails_before_remote_intake(tmp_path, payload):
    instance = server(tmp_path)
    (Path(instance.data['dir']) / 'steam_appid.txt').unlink()
    with pytest.raises(ServerError, match='game AppID'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []


def test_explicit_module_identity_can_work_without_server_files(tmp_path, payload):
    instance = server(tmp_path, workshop_app_id=550)
    (Path(instance.data['dir']) / 'steam_appid.txt').unlink()
    downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == [(550, '10', True)]


def test_conflicting_installed_appids_are_rejected(tmp_path, payload):
    instance = server(tmp_path)
    binary_dir = Path(instance.data['dir']) / 'bin'
    binary_dir.mkdir()
    (binary_dir / 'steam_appid.txt').write_text('730')
    with pytest.raises(ServerError, match='conflicting'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []


def test_workshop_cache_cannot_supply_its_own_game_identity(tmp_path, payload):
    instance = server(tmp_path)
    cache = Path(instance.data['dir']) / 'steamapps/workshop/content/730/123'
    cache.mkdir(parents=True)
    (cache / 'steam_appid.txt').write_text('730')
    assert downloads.resolve_server_workshop_app_id(instance) == 550


def test_wrong_game_rejected_before_downloading(tmp_path, payload, monkeypatch):
    instance = server(tmp_path)
    def wrong_game(*args):
        raise workshop.ModSupportError('expected 550')
    monkeypatch.setattr(workshop, 'resolve_workshop_item', wrong_game)
    with pytest.raises(ServerError, match='expected 550'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []


def test_staging_symlink_rejected_without_download(tmp_path, payload):
    instance = server(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    (Path(instance.data['dir']) / '.alphagsm').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError, match='symlink|outside'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []
    assert list(outside.iterdir()) == []


def test_partial_download_failure_keeps_completed_items_tracked(tmp_path, payload, monkeypatch):
    instance = server(tmp_path)
    original = downloads.steamcmd.download_workshop_item
    def download(path, app, item, anonymous):
        if item == '11':
            raise subprocess.CalledProcessError(1, ['steamcmd'], output='Access Denied')
        return original(path, app, item, anonymous)
    monkeypatch.setattr(downloads.steamcmd, 'download_workshop_item', download)
    with pytest.raises(ServerError, match='Access Denied'):
        downloads.run_workshop_command(instance, 'download', 'collection', '1')
    assert instance.data['workshop_downloads']['items'][0]['workshop_id'] == '10'


def test_nonanonymous_servers_rejected_even_if_store_flag_changed(tmp_path, payload):
    instance = server(tmp_path)
    instance.module.steam_anonymous_login_possible = False
    instance.data['Steam_anonymous_login_possible'] = True
    with pytest.raises(ServerError, match='anonymous'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []


def test_server_cli_dispatches_shared_workshop_command(tmp_path, monkeypatch):
    instance = Server.__new__(Server)
    fixture = server(tmp_path)
    instance.module = fixture.module
    instance.module.commands = ()
    instance.module.command_args = {}
    instance.module.command_descriptions = {}
    instance.data = fixture.data
    calls = []
    monkeypatch.setattr(downloads, 'run_workshop_command', lambda *args, **kwargs: calls.append(args))
    assert 'workshop' in instance.get_commands()
    assert instance.get_command_args('workshop') is not None
    assert 'download' in instance.get_command_description('workshop').lower()
    instance.run_command('workshop', 'download', 'item', '10')
    assert calls == [(instance, 'download', 'item', '10')]
    instance.module.steam_anonymous_login_possible = False
    assert 'workshop' not in instance.get_commands()


def test_every_anonymous_steamcmd_module_exposes_shared_workshop_command():
    count = 0
    for module_name in load_default_module_catalog().canonical_modules:
        module = import_module("gamemodules." + module_name)
        anonymous = getattr(module, 'steam_anonymous_login_possible', None)
        family = getattr(module, 'MODULE', None)
        if anonymous is None:
            anonymous = getattr(family, 'steam_anonymous_login_possible', None)
        if anonymous is not True:
            continue
        instance = Server.__new__(Server)
        instance.module = module
        instance.data = Data(module=module_name)
        assert downloads.supports_anonymous_workshop(instance), module_name
        assert 'workshop' in instance.get_commands(), module_name
        assert instance.get_command_args('workshop') is not None, module_name
        count += 1
    assert count >= 150, f'Anonymous SteamCMD coverage unexpectedly fell to {count}'


def test_refresh_replaces_obsolete_staged_files(tmp_path, payload):
    instance = server(tmp_path)
    downloads.run_workshop_command(instance, 'download', 'item', '10')
    upstream = tmp_path / 'steam-content'
    (upstream / 'addon.vpk').unlink()
    (upstream / 'replacement.vpk').write_bytes(b'new addon')
    downloads.run_workshop_command(instance, 'download', 'item', '10')
    staged = Path(instance.data['dir']) / '.alphagsm/workshop/content/550/10'
    assert sorted(path.name for path in staged.iterdir()) == ['replacement.vpk']
    assert len(instance.data['workshop_downloads']['items']) == 1


@pytest.mark.parametrize('relative', ['.alphagsm/workshop/cache',
    '.alphagsm/workshop/cache/steamapps/workshop/content/550/10',
    '.alphagsm/workshop/cache/steamapps/workshop/appworkshop_550.acf'])
def test_cache_symlinks_rejected_before_steamcmd(tmp_path, payload, relative):
    instance = server(tmp_path)
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = Path(instance.data['dir']) / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError, match='symlink|outside'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []


def test_oversized_installed_identity_is_rejected(tmp_path, payload):
    instance = server(tmp_path)
    (Path(instance.data['dir']) / 'steam_appid.txt').write_text('550' + ' ' * 40 + '730')
    with pytest.raises(ServerError):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == []


def test_failed_refresh_publication_restores_previous_download(tmp_path, payload, monkeypatch):
    instance = server(tmp_path)
    downloads.run_workshop_command(instance, 'download', 'item', '10')
    original = Path.rename
    def fail_fresh_rename(path, target):
        if path.name == 'payload':
            raise OSError('simulated publish failure')
        return original(path, target)
    monkeypatch.setattr(Path, 'rename', fail_fresh_rename)
    with pytest.raises(ServerError, match='publish failure'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    staged = Path(instance.data['dir']) / '.alphagsm/workshop/content/550/10/addon.vpk'
    assert staged.read_bytes() == b'addon'
    assert len(instance.data['workshop_downloads']['items']) == 1


def test_source_gameinfo_identity_precedes_server_tool_appid_file(tmp_path, payload):
    instance = server(tmp_path)
    instance.data['game_dir'] = 'left4dead2'
    (Path(instance.data['dir']) / 'steam_appid.txt').write_text('222860')
    game = Path(instance.data['dir']) / 'left4dead2'
    game.mkdir()
    (game / 'gameinfo.txt').write_text('"FileSystem" { "SteamAppId" "550" }')
    downloads.run_workshop_command(instance, 'download', 'item', '10')
    assert payload == [(550, '10', True)]


def test_failed_refresh_and_rollback_preserve_recoverable_previous_payload(tmp_path, payload, monkeypatch):
    instance = server(tmp_path)
    downloads.run_workshop_command(instance, 'download', 'item', '10')
    destination = Path(instance.data['dir']) / '.alphagsm/workshop/content/550/10'
    original = Path.rename
    def fail_destination_rename(path, target):
        if Path(target) == destination:
            raise OSError('destination unavailable')
        return original(path, target)
    monkeypatch.setattr(Path, 'rename', fail_destination_rename)
    with pytest.raises(ServerError, match='previous|retained|recover'):
        downloads.run_workshop_command(instance, 'download', 'item', '10')
    managed = Path(instance.data['dir']) / '.alphagsm/workshop'
    backups = list(managed.glob('.previous-*/addon.vpk'))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b'addon'
    assert str(backups[0].parent) in instance.data['workshop_downloads']['errors'][0]
