"""Native Workshop desired state and safe config publication contracts."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from server import ServerError
from server.modsupport import native_workshop as native
from server.modsupport.errors import ModSupportError


class Data(dict):
    """Datastore with an observable save operation."""
    def save(self):
        self['saves'] = self.get('saves', 0) + 1


@pytest.fixture
def native_server(tmp_path):
    return SimpleNamespace(data=Data(dir=str(tmp_path)), name='native')


@pytest.fixture
def support(monkeypatch):
    monkeypatch.setattr(native.workshop, 'resolve_workshop_item',
                        lambda value, _app: {'workshop_id': value, 'resolved_id': f'workshop.{value}'})
    monkeypatch.setattr(native.workshop, 'resolve_workshop_items', lambda values, _app: values)
    monkeypatch.setattr(native.workshop, 'resolve_workshop_collection', lambda _value, _app: ['10', '20'])
    callback = Mock(return_value=['cfg/mods.json'])
    adapter = native.build_native_workshop_support(
        game_label='Native', workshop_app_id=550, apply_callback=callback)
    return adapter, callback


def test_collection_import_deduplicates_and_canonicalizes(native_server, support):
    adapter, _callback = support
    command = adapter.command_functions['mod']
    command(native_server, 'add', 'workshop', 'https://steamcommunity.com/sharedfiles/filedetails/?id=10')
    command(native_server, 'add', 'workshop-collection', '30')
    desired = native_server.data['mods']['desired']['workshop']
    assert [entry['workshop_id'] for entry in desired] == ['10', '20']
    assert desired[1]['collection_id'] == '30'
    command(native_server, 'remove', 'workshop', 'https://steamcommunity.com/sharedfiles/filedetails/?id=10')
    assert [entry['workshop_id'] for entry in desired] == ['20']


def test_rejected_collection_does_not_mutate_desired(native_server, support, monkeypatch):
    adapter, _callback = support
    command = adapter.command_functions['mod']
    command(native_server, 'add', 'workshop', '10')
    def reject(*_args):
        raise ModSupportError('Wrong game')
    monkeypatch.setattr(native.workshop, 'resolve_workshop_collection', reject)
    with pytest.raises(ServerError, match='Wrong game'):
        command(native_server, 'add', 'workshop-collection', '30')
    assert len(native_server.data['mods']['desired']['workshop']) == 1


def test_apply_preflights_all_items_before_native_writes(native_server, support, monkeypatch):
    adapter, callback = support
    adapter.command_functions['mod'](native_server, 'add', 'workshop-collection', '30')
    def reject(*_args):
        raise ModSupportError('Unavailable item')
    monkeypatch.setattr(native.workshop, 'resolve_workshop_items', reject)
    with pytest.raises(ServerError, match='Unavailable'):
        adapter.apply_configured_mods(native_server)
    callback.assert_not_called()
    assert native_server.data['mods']['errors']


def test_configured_state_does_not_claim_runtime_load(native_server, support):
    adapter, callback = support
    adapter.command_functions['mod'](native_server, 'add', 'workshop', '10')
    adapter.apply_configured_mods(native_server)
    callback.assert_called_once_with(native_server, ['10'])
    state = native_server.data['mods']['native_workshop']
    assert state == {'workshop_ids': ['10'], 'config_files': ['cfg/mods.json'], 'status': 'configured'}


def test_cleanup_clears_desired_after_empty_native_configuration(native_server, support):
    adapter, callback = support
    adapter.command_functions['mod'](native_server, 'add', 'workshop', '10')
    adapter.cleanup_configured_mods(native_server)
    callback.assert_called_with(native_server, [])
    assert native_server.data['mods']['desired']['workshop'] == []


def test_disabled_apply_preserves_desired(native_server, support):
    adapter, callback = support
    adapter.command_functions['mod'](native_server, 'add', 'workshop', '10')
    native_server.data['mods']['enabled'] = False
    adapter.apply_configured_mods(native_server)
    callback.assert_called_with(native_server, [])
    assert native_server.data['mods']['desired']['workshop'][0]['workshop_id'] == '10'


def test_native_failure_retains_last_configured_state(native_server, support):
    adapter, callback = support
    adapter.command_functions['mod'](native_server, 'add', 'workshop', '10')
    adapter.apply_configured_mods(native_server)
    previous = native_server.data['mods']['native_workshop'].copy()
    callback.side_effect = OSError('disk full')
    with pytest.raises(ServerError, match='disk full'):
        adapter.apply_configured_mods(native_server)
    assert native_server.data['mods']['native_workshop'] == previous


@pytest.mark.parametrize('relative', ['../outside', '/tmp/outside', 'cfg/../outside', '.'])
def test_config_paths_reject_escape(native_server, relative):
    with pytest.raises(ServerError):
        native.safe_server_path(native_server, relative)


def test_write_rejects_symlink_before_touching_target(native_server, tmp_path):
    outside = tmp_path.parent / f'{tmp_path.name}-outside'
    outside.mkdir()
    (tmp_path / 'cfg').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError, match='symlink'):
        native.write_managed_text(native_server, 'cfg/mods.json', '{}')
    assert not (outside / 'mods.json').exists()


def test_atomic_write_cleans_temporary_and_preserves_old_on_failure(native_server, monkeypatch):
    path = native.write_managed_text(native_server, 'cfg/mods.json', 'old')
    def reject(_self, _target):
        raise OSError('publish failed')
    monkeypatch.setattr(Path, 'replace', reject)
    with pytest.raises(OSError, match='publish failed'):
        native.write_managed_text(native_server, 'cfg/mods.json', 'new')
    assert path.read_text() == 'old'
    assert list(path.parent.iterdir()) == [path]
