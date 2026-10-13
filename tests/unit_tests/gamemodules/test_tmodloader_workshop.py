"""tModLoader native package validation, configuration and ownership."""

import hashlib
import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from gamemodules.terraria import tmodloader as module
from gamemodules.terraria.tmodloader import workshop as support
from server.errors import ServerError
from tests.unit_tests.gamemodules.helpers import DummyData


def _string(value):
    raw = value.encode()
    return bytes([len(raw)]) + raw


def _tmod(path, name='ServerFeature', version='2026.8.3.0', entry='Info'):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (_string(name) + _string('1.0') + struct.pack('<i', 1)
            + _string(entry) + struct.pack('<ii', 4, 4) + b'data')
    header = (b'TMOD' + _string(version) + hashlib.sha1(data).digest()
              + bytes(256) + struct.pack('<i', len(data)))
    path.write_bytes(header + data)
    return path


@pytest.fixture
def server(tmp_path):
    return SimpleNamespace(name='tml', module=module, data=DummyData(
        dir=str(tmp_path), port=7777, world='tml.wld', worldname='tml', worldsize=1,
        maxplayers=8, version='v2026.08.3.0', serverpassword=''))


def test_module_exposes_native_workshop_and_runtime_contract():
    assert module.workshop_app_id == 1281930
    assert module.steam_anonymous_login_possible is True
    assert 'mod' in module.commands
    assert callable(module.get_container_spec)


def test_package_header_and_payload_hash_are_verified(tmp_path):
    path = _tmod(tmp_path / 'feature.tmod')
    assert support.inspect_tmod(path) == ('ServerFeature', (2026, 8, 3, 0))
    raw = bytearray(path.read_bytes())
    raw[-1] ^= 1
    path.write_bytes(raw)
    with pytest.raises(ServerError, match='hash'):
        support.inspect_tmod(path)


@pytest.mark.parametrize('name,entry', [('../escape', 'Info'), ('Feature', '../outside'),
                                      ('Feature', '/absolute'), ('Feature', 'a\\b')])
def test_unsafe_package_metadata_is_rejected(tmp_path, name, entry):
    path = _tmod(tmp_path / 'bad.tmod', name=name, entry=entry)
    with pytest.raises(ServerError):
        support.inspect_tmod(path)


def test_selects_latest_compatible_package_and_rejects_future_only(tmp_path):
    root = tmp_path / 'payload'
    _tmod(root / 'older/Feature.tmod', version='2025.1.1.0')
    newest = _tmod(root / 'stable/Feature.tmod', version='2026.8.3.0')
    future = _tmod(root / 'future/Feature.tmod', version='2027.1.1.0')
    assert support.select_workshop_packages({'1': root}, 'v2026.08.3.0') == {
        'ServerFeature': newest}
    newest.unlink()
    (root / 'older/Feature.tmod').unlink()
    with pytest.raises(ServerError, match='compatible'):
        support.select_workshop_packages({'1': root}, 'v2026.08.3.0')
    assert future.exists()


def test_duplicate_internal_names_across_items_are_rejected(tmp_path):
    one = tmp_path / 'one'
    two = tmp_path / 'two'
    _tmod(one / 'Feature.tmod')
    _tmod(two / 'Feature.tmod')
    with pytest.raises(ServerError, match='Duplicate'):
        support.select_workshop_packages({'1': one, '2': two}, 'v2026.08.3.0')


def test_native_apply_and_cleanup_preserve_operator_mods(server, tmp_path, monkeypatch):
    root = tmp_path / 'cache'
    _tmod(root / 'Feature.tmod')
    monkeypatch.setattr(support, 'download_workshop_items', lambda *_: {'1': root})
    enabled = tmp_path / 'Mods/enabled.json'
    enabled.parent.mkdir()
    enabled.write_text('["OperatorFeature"]')
    support.apply_workshop_mods(server, ['1'])
    assert json.loads(enabled.read_text()) == ['OperatorFeature', 'ServerFeature']
    assert (tmp_path / 'Mods/ServerFeature.tmod').is_file()
    support.apply_workshop_mods(server, [])
    assert json.loads(enabled.read_text()) == ['OperatorFeature']
    assert not (tmp_path / 'Mods/ServerFeature.tmod').exists()


def test_payload_failure_restores_enabled_config_and_ownership(server, tmp_path, monkeypatch):
    root = tmp_path / 'cache'
    _tmod(root / 'Feature.tmod')
    monkeypatch.setattr(support, 'download_workshop_items', lambda *_: {'1': root})
    enabled = tmp_path / 'Mods/enabled.json'
    enabled.parent.mkdir()
    enabled.write_text('["OperatorFeature"]')
    def reject(*_args):
        raise ServerError('collision')
    monkeypatch.setattr(support.owned_payloads, 'publish_owned_payloads', reject)
    with pytest.raises(ServerError, match='collision'):
        support.apply_workshop_mods(server, ['1'])
    assert enabled.read_text() == '["OperatorFeature"]'
    assert not server.data.get('mods', {}).get('tmodloader_owned_names')


def test_config_sync_and_launch_are_unattended_and_contained(server, tmp_path):
    (tmp_path / 'start-tModLoaderServer.sh').write_text('#!/bin/bash\n')
    (tmp_path / 'serverconfig.txt').write_text('# operator\ncustom=keep\nport=1\n')
    module.sync_server_config(server)
    text = (tmp_path / 'serverconfig.txt').read_text()
    assert '# operator' in text and 'custom=keep' in text
    assert 'port=7777' in text and 'modpath=Mods' in text
    command, directory = module.get_start_command(server, autocreate=True)
    assert command[:3] == ['bash', 'start-tModLoaderServer.sh', '-nosteam']
    assert '-autocreate' in command and directory == str(tmp_path)
    assert module.get_query_address(server)[2] == 'terraria'
    module.prestart(server, autocreate=True)
    with pytest.raises(ServerError):
        module.checkvalue(server, ['world'], '../outside.wld')


def test_release_resolver_selects_official_named_asset(monkeypatch):
    monkeypatch.setattr(module.github_releases, 'read_json', lambda *_: {
        'tag_name': 'v2026.08.3.0', 'assets': [
            {'name': 'ExampleMod.zip', 'browser_download_url': 'https://example.invalid/example.zip'},
            {'name': 'tModLoader.zip', 'browser_download_url': 'https://github.com/tModLoader/tModLoader/releases/download/v2026.08.3.0/tModLoader.zip'}]})
    version, url = module.resolve_tmodloader_download()
    assert version == 'v2026.08.3.0' and url.endswith('/tModLoader.zip')
