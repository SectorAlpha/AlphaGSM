"""Public-only dispatch must not load the manager or accept private protocols."""
import bz2
import json
import struct
import sys
import subprocess
import pytest
from server.public_query import query_public, PROFILES
from utils import query


class Socket:
    def __init__(self, packets):
        self.packets = iter(packets)
        self.sent = []
    def __enter__(self):
        return self
    def __exit__(self, *_):
        pass
    def connect(self, address):
        self.address = address
    def settimeout(self, timeout):
        assert timeout > 0
    def sendto(self, data, address):
        self.sent.append((data, address))
    def recv(self, size):
        return next(self.packets)


def fragment(message, total, index, payload):
    return b'\xfe\xff\xff\xff' + struct.pack('<IBBH', message, total, index, 1248) + payload


@pytest.mark.parametrize('packets', [
    [fragment(1, 0, 0, b'x')],
    [fragment(1, 2, 2, b'x')],
    [fragment(1, 2, 0, b'x'), fragment(2, 2, 1, b'y')],
    [fragment(1, 2, 0, b'x'), fragment(1, 2, 0, b'y')],
    [fragment(0x80000001, 1, 0, struct.pack('<II', 300000, 0) + bz2.compress(b'x'*300000))],
])
def test_hostile_fragments_fail_bounded(monkeypatch, packets):
    monkeypatch.setattr(query.socket, 'socket', lambda *a: Socket(packets))
    with pytest.raises(query.QueryError):
        query.a2s_info('8.8.8.8', 27015)


def test_public_registry_and_normalization(monkeypatch):
    monkeypatch.setattr(query, 'slp_info', lambda *a, **kw: dict(description='hello',
        players_online=2, players_max=20, version='1.21', player_names=['private']))
    result = query_public('minecraft.vanilla', '8.8.8.8', 25565, virtual_host='game.example')
    assert result == dict(name='hello', players=2, capacity=20, version='1.21')
    subprocess.run([sys.executable, '-c', "from server.public_query import PROFILES; import sys; assert 'server.server' not in sys.modules; assert 'core' not in sys.modules"], check=True, timeout=5)
    with pytest.raises(query.QueryError):
        query_public('teamspeak', '8.8.8.8', 10011)
    with pytest.raises(TypeError):
        PROFILES['custom'] = 'http'


def test_invalid_counts_fail(monkeypatch):
    monkeypatch.setattr(query, 'slp_info', lambda *a, **kw: dict(description='', players_online=-1,
                                                              players_max=20, version=''))
    with pytest.raises(query.QueryError):
        query_public('minecraft.vanilla', '8.8.8.8', 25565)
