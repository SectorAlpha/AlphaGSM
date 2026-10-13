"""Native payload publication must preserve operator files and recover failures."""

from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from server.errors import ServerError
from server.modsupport import owned_payloads as owned


class Data(dict):
    """Small observable datastore."""

    def save(self):
        """Persisting is observable without a real AlphaGSM database."""
        self['saves'] = self.get('saves', 0) + 1


@pytest.fixture
def server(tmp_path):
    return SimpleNamespace(data=Data(dir=str(tmp_path)), name='owned')


def test_publish_refresh_and_cleanup_preserve_operator_extras(server, tmp_path):
    source = tmp_path / 'cache' / 'mod.pak'
    source.parent.mkdir()
    source.write_bytes(b'first')
    owned.publish_owned_payloads(server, 'test', {'Mods/item/mod.pak': source})
    extra = tmp_path / 'Mods/item/operator.txt'
    extra.write_text('operator')
    owned.publish_owned_payloads(server, 'test', {'Mods/item/new.pak': b'second'})
    assert not (tmp_path / 'Mods/item/mod.pak').exists()
    assert (tmp_path / 'Mods/item/new.pak').read_bytes() == b'second'
    owned.cleanup_owned_payloads(server, 'test')
    assert extra.read_text() == 'operator'
    assert not (tmp_path / 'Mods/item/new.pak').exists()


def test_collision_preflight_does_not_publish_any_file(server, tmp_path):
    target = tmp_path / 'Mods/operator.pak'
    target.parent.mkdir()
    target.write_bytes(b'operator')
    with pytest.raises(ServerError, match='unowned'):
        owned.publish_owned_payloads(server, 'test', {
            'Mods/new.pak': b'new', 'Mods/operator.pak': b'replacement'})
    assert target.read_bytes() == b'operator'
    assert not (tmp_path / 'Mods/new.pak').exists()


def test_external_edits_block_refresh_and_cleanup(server, tmp_path):
    owned.publish_owned_payloads(server, 'test', {'Mods/owned.pak': b'original'})
    target = tmp_path / 'Mods/owned.pak'
    target.write_bytes(b'operator edit')
    with pytest.raises(ServerError, match='modified'):
        owned.publish_owned_payloads(server, 'test', {'Mods/new.pak': b'new'})
    with pytest.raises(ServerError, match='modified'):
        owned.cleanup_owned_payloads(server, 'test')
    assert target.read_bytes() == b'operator edit'
    assert not (tmp_path / 'Mods/new.pak').exists()


def test_other_owner_cannot_take_over_managed_file(server, tmp_path):
    owned.publish_owned_payloads(server, 'first', {'Mods/mod.pak': b'first'})
    with pytest.raises(ServerError, match='owner'):
        owned.publish_owned_payloads(server, 'second', {'Mods/mod.pak': b'second'})
    assert (tmp_path / 'Mods/mod.pak').read_bytes() == b'first'


@pytest.mark.parametrize('destination', ['../outside', '/outside', '.', 'Mods/../outside'])
def test_escaping_destinations_are_rejected(server, destination):
    with pytest.raises(ServerError):
        owned.publish_owned_payloads(server, 'test', {destination: b'bad'})


def test_symlink_destination_and_source_are_rejected(server, tmp_path):
    outside = tmp_path.parent / (tmp_path.name + '-outside')
    outside.mkdir()
    (tmp_path / 'Mods').symlink_to(outside, target_is_directory=True)
    with pytest.raises(ServerError, match='symlink'):
        owned.publish_owned_payloads(server, 'test', {'Mods/new.pak': b'bad'})
    (tmp_path / 'Mods').unlink()
    source = tmp_path / 'source.pak'
    source.symlink_to(outside / 'source.pak')
    with pytest.raises(ServerError, match='symlink'):
        owned.publish_owned_payloads(server, 'test', {'Mods/new.pak': source})
    assert not list(outside.iterdir())


def test_source_must_be_inside_server_root(server, tmp_path):
    source = tmp_path.parent / (tmp_path.name + '-source.pak')
    source.write_bytes(b'outside')
    with pytest.raises(ServerError, match='source'):
        owned.publish_owned_payloads(server, 'test', {'Mods/mod.pak': source})


def test_failed_publication_rolls_back_entire_batch(server, tmp_path, monkeypatch):
    owned.publish_owned_payloads(server, 'test', {'Mods/old.pak': b'old'})
    previous = server.data['mods']['owned_payloads']['test'].copy()
    original = owned.os.replace
    failed = False

    def fail_second(source, destination):
        nonlocal failed
        if Path(destination).name == 'second.pak' and not failed:
            failed = True
            raise OSError('disk full')
        return original(source, destination)

    monkeypatch.setattr(owned.os, 'replace', fail_second)
    with pytest.raises(OSError, match='disk full'):
        owned.publish_owned_payloads(server, 'test', {
            'Mods/first.pak': b'first', 'Mods/second.pak': b'second'})
    assert (tmp_path / 'Mods/old.pak').read_bytes() == b'old'
    assert not (tmp_path / 'Mods/first.pak').exists()
    assert not (tmp_path / 'Mods/second.pak').exists()
    assert server.data['mods']['owned_payloads']['test'] == previous


def test_case_and_file_directory_aliases_fail_before_mutation(server, tmp_path):
    for files in ({'Mods/A.pak': b'a', 'Mods/a.pak': b'b'},
                  {'Mods/item': b'a', 'Mods/item/mod.pak': b'b'}):
        with pytest.raises(ServerError):
            owned.publish_owned_payloads(server, 'test', files)
    assert not (tmp_path / 'Mods').exists()


def test_save_failure_restores_files_and_manifest(server, tmp_path, monkeypatch):
    owned.publish_owned_payloads(server, 'test', {'Mods/old.pak': b'old'})
    previous = server.data['mods']['owned_payloads']['test'].copy()
    def reject_save():
        raise OSError('database full')
    monkeypatch.setattr(server.data, 'save', reject_save)
    with pytest.raises(OSError, match='database full'):
        owned.publish_owned_payloads(server, 'test', {'Mods/new.pak': b'new'})
    assert (tmp_path / 'Mods/old.pak').read_bytes() == b'old'
    assert not (tmp_path / 'Mods/new.pak').exists()
    assert server.data['mods']['owned_payloads']['test'] == previous


def test_failed_rollback_keeps_recoverable_original_payload(server, tmp_path, monkeypatch):
    owned.publish_owned_payloads(server, 'test', {'Mods/old.pak': b'old'})
    original = owned.os.replace
    def fail_native_destinations(source, destination):
        if Path(destination).parent.name == 'Mods':
            raise OSError('filesystem unavailable')
        return original(source, destination)
    monkeypatch.setattr(owned.os, 'replace', fail_native_destinations)
    with pytest.raises(ServerError, match='recovery'):
        owned.publish_owned_payloads(server, 'test', {'Mods/new.pak': b'new'})
    backups = list((tmp_path / '.alphagsm/owned-payloads').glob('.transaction-*/old-*'))
    assert len(backups) == 1 and backups[0].read_bytes() == b'old'
    recovery = json.loads((backups[0].parent / 'recovery.json').read_text())
    assert recovery['owner'] == 'test'
    assert recovery['files']['Mods/old.pak']['backup'] == 'old-0'
