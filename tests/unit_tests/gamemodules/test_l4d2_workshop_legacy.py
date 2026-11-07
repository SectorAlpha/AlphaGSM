"""Legacy Steam Workshop upload names only become addons after VPK validation."""

import struct
from types import SimpleNamespace

import pytest

from gamemodules.l4d2server import main


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('previous', [False, True])
def test_legacy_workshop_payload_normalizes_valid_vpk(tmp_path, monkeypatch, version, previous):
    payload = tmp_path / '123_legacy.bin'
    header = struct.pack('<III', 0x55AA1234, version, 1)
    payload.write_bytes(header + (bytes(16) if version == 2 else b'') + b'\x00')
    if previous:
        (tmp_path / '10.vpk').write_bytes(b'old content')
    monkeypatch.setattr(main.steamcmd, 'download_workshop_item', lambda *args: str(tmp_path))
    assert main._download_workshop_vpk(tmp_path, 550, '10', True) == str(tmp_path)
    assert (tmp_path / '10.vpk').read_bytes().startswith(header)
    assert not payload.exists()


@pytest.mark.parametrize('payload', [b'not-vpk', struct.pack('<III', 0x55AA1234, 3, 1),
                                     struct.pack('<III', 0x55AA1234, 1, 100)])
def test_legacy_non_vpk_payload_is_rejected(tmp_path, monkeypatch, payload):
    (tmp_path / '123_legacy.bin').write_bytes(payload)
    monkeypatch.setattr(main.steamcmd, 'download_workshop_item', lambda *args: str(tmp_path))
    with pytest.raises(RuntimeError, match='not a VPK'):
        main._download_workshop_vpk(tmp_path, 550, '10', True)
    assert not (tmp_path / '10.vpk').exists()


def test_docker_console_has_terminal_for_native_addon_probe(monkeypatch, tmp_path):
    server = SimpleNamespace(data={'dir': str(tmp_path), 'port': 27015, 'clientport': 27005})
    monkeypatch.setattr(main.runtime_module, 'build_container_spec', lambda instance, **kwargs: kwargs)
    spec = main.get_container_spec(server)
    assert spec['stdin_open'] is True
    assert spec['tty'] is True


def test_ambiguous_legacy_payload_cannot_reuse_old_vpk(tmp_path, monkeypatch):
    (tmp_path / '10.vpk').write_bytes(b'stale')
    for name in ['123_legacy.bin', '456_legacy.bin']:
        (tmp_path / name).write_bytes(struct.pack('<III', 0x55AA1234, 1, 1) + b'\x00')
    monkeypatch.setattr(main.steamcmd, 'download_workshop_item', lambda *args: str(tmp_path))
    with pytest.raises(RuntimeError, match='one VPK'):
        main._download_workshop_vpk(tmp_path, 550, '10', True)
    assert (tmp_path / '10.vpk').read_bytes() == b'stale'
