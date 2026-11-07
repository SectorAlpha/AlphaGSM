"""Squad native RCON metadata, framing and secret isolation."""

import json

import pytest

from utils import query
from tests.unit_tests.utils.test_source_rcon import _Socket, _packet


def test_squad_queries_actual_server_metadata_and_discards_extra_fields(monkeypatch):
    payload = json.dumps({'PlayerCount_I': '3', 'MaxPlayers': 80,
                          'MapName_s': 'Unknown', 'ServerName_s': 'My Squad',
                          'GameMode_s': 'AAS', 'GameVersion_s': 'v10.6',
                          'AdminPassword': 'do-not-print'})
    sock = _Socket([_packet(1, 0, ''), _packet(1, 2, ''),
                    _packet(2, 0, payload[:50]), _packet(2, 0, payload[50:])])
    map_sock = _Socket([_packet(1, 2, ''), _packet(2, 0,
        'Current level is Al Basrah, layer is AlBasrah_AAS_v1, factions USMC MEI')])
    sockets = iter([sock, map_sock])
    monkeypatch.setattr(query.socket, 'create_connection', lambda *_a, **_k: next(sockets))
    result = query.squad_rcon_info('host', 21114, 'secret')
    assert result == {'players': 3, 'max_players': 80, 'map': 'Al Basrah',
                      'layer': 'AlBasrah_AAS_v1',
                      'name': 'My Squad', 'gamemode': 'AAS', 'version': 'v10.6'}
    assert b'ShowServerInfo\x00\x00' in sock.sent[1]
    assert b'ShowCurrentMap\x00\x00' in map_sock.sent[1]
    assert 'secret' not in json.dumps(result)
    assert 'do-not-print' not in json.dumps(result)


@pytest.mark.parametrize('body', ['not json', '[]', '{}',
    '{"PlayerCount_I":"bad","MaxPlayers":80}',
    '{"PlayerCount_I":true,"MaxPlayers":80}',
    '{"PlayerCount_I":"81","MaxPlayers":80}'])
def test_invalid_squad_response_never_counts_as_readiness(monkeypatch, body):
    sock = _Socket([_packet(1, 2, ''), _packet(2, 0, body)])
    monkeypatch.setattr(query.socket, 'create_connection', lambda *_a, **_k: sock)
    with pytest.raises(query.QueryError, match='Squad'):
        query.squad_rcon_info('host', 21114, 'secret')


def test_squad_rejects_failed_authentication(monkeypatch):
    sock = _Socket([_packet(-1, 2, '')])
    monkeypatch.setattr(query.socket, 'create_connection', lambda *_a, **_k: sock)
    with pytest.raises(query.QueryError, match='authentication failed'):
        query.squad_rcon_info('host', 21114, 'wrong')


@pytest.mark.parametrize('current', ['Not loaded',
    'Current level is Unknown, layer is Unknown, factions USMC MEI'])
def test_squad_requires_actual_loaded_map_and_layer(monkeypatch, current):
    sockets = iter([_Socket([_packet(1, 2, ''), _packet(2, 0,
        '{"PlayerCount_I":"0","MaxPlayers":80}')]),
        _Socket([_packet(1, 2, ''), _packet(2, 0, current)])])
    monkeypatch.setattr(query.socket, 'create_connection', lambda *_a, **_k: next(sockets))
    with pytest.raises(query.QueryError, match='loaded map'):
        query.squad_rcon_info('host', 21114, 'secret')


@pytest.mark.parametrize('elapsed,expected_calls', [(0.75, 2), (1.1, 1)])
def test_squad_commands_share_one_total_deadline(monkeypatch, elapsed, expected_calls):
    clock = iter([100.0, 100.0 + elapsed])
    monkeypatch.setattr(query.time, 'monotonic', lambda: next(clock))
    calls = []
    def command(_host, _port, _password, timeout, name):
        calls.append((name, timeout))
        if name == 'ShowServerInfo':
            return '{"PlayerCount_I":"0","MaxPlayers":80}'
        return 'Current level is Al Basrah, layer is AlBasrah_AAS_v1, factions USMC MEI'
    monkeypatch.setattr(query, '_source_rcon_command_once', command)
    if elapsed > 1:
        with pytest.raises(query.QueryError, match='timed out'):
            query.squad_rcon_info('host', 21114, 'secret', timeout=1)
    else:
        assert query.squad_rcon_info('host', 21114, 'secret', timeout=1)['players'] == 0
        assert calls[1] == ('ShowCurrentMap', 0.25)
    assert len(calls) == expected_calls
