"""Exercise the classic Soldat file query without opening network sockets."""

from unittest.mock import MagicMock

import pytest

import utils.query as query_module


RESPONSE = b"Players: 2\r\nMap: ctf_Ash\r\nGamemode: Capture the Flag\r\nENDFILES\r\n"
REQUEST = b"STARTFILES\r\nlogs/gamestat.txt\r\nENDFILES\r\n"


def mock_socket(monkeypatch, chunks):
    sock = MagicMock()
    sock.__enter__.return_value = sock
    sock.recv.side_effect = chunks
    connect = MagicMock(return_value=sock)
    monkeypatch.setattr(query_module.socket, "create_connection", connect)
    return sock, connect


@pytest.mark.parametrize("chunks", [[RESPONSE], [RESPONSE[:5], RESPONSE[5:-4], RESPONSE[-4:]]])
def test_soldat_reads_only_fixed_status_file_and_reassembles_response(monkeypatch, chunks):
    sock, connect = mock_socket(monkeypatch, chunks)
    result = query_module.soldat_info("192.0.2.1", 23083)
    assert result == {"players": 2, "map": "ctf_Ash", "gamemode": "Capture the Flag"}
    assert connect.call_args.args[0] == ("192.0.2.1", 23083)
    sock.sendall.assert_called_once_with(REQUEST)
    assert sock.__exit__.called


def test_soldat_accepts_zero_players_without_optional_gamemode(monkeypatch):
    mock_socket(monkeypatch, [b"Players: 0\r\nMap: Arena\r\nENDFILES\r\n"])
    assert query_module.soldat_info("localhost", 23083) == {"players": 0, "map": "Arena"}


@pytest.mark.parametrize("response", [
    b"ENDFILES\r\n",
    b"Players: 2\r\nENDFILES\r\n",
    b"Players: invalid\r\nMap: Arena\r\nENDFILES\r\n",
    b"Players: -1\r\nMap: Arena\r\nENDFILES\r\n",
    b"Players: 2\r\nMap: \r\nENDFILES\r\n",
    b"Players: 2\r\nMap: Arena\r\n",
    b"Players: 2\r\nMap: Arena\r\nENDFILES",
])
def test_soldat_rejects_incomplete_or_malformed_status(monkeypatch, response):
    sock, _ = mock_socket(monkeypatch, [response, b""])
    with pytest.raises(query_module.QueryError):
        query_module.soldat_info("localhost", 23083)
    assert sock.__exit__.called


def test_soldat_rejects_oversized_response(monkeypatch):
    sock, _ = mock_socket(monkeypatch, [b"x" * 4096] * 17)
    with pytest.raises(query_module.QueryError, match="64 KiB"):
        query_module.soldat_info("localhost", 23083)
    assert sock.recv.call_count <= 17


@pytest.mark.parametrize("stage", ["connect", "send", "recv"])
def test_soldat_wraps_socket_failures_and_never_uses_reachability_fallback(monkeypatch, stage):
    sock, connect = mock_socket(monkeypatch, [RESPONSE])
    target = {"connect": connect, "send": sock.sendall, "recv": sock.recv}[stage]
    target.side_effect = TimeoutError("fixture timeout")
    monkeypatch.setattr(query_module, "tcp_ping", MagicMock(side_effect=AssertionError("no fallback")))
    with pytest.raises(query_module.QueryError, match="fixture timeout"):
        query_module.soldat_info("localhost", 23083)


def test_soldat_uses_one_deadline_across_fragments(monkeypatch):
    sock, _ = mock_socket(monkeypatch, [b"Players: 2\r\n", b"Map: Arena\r\n", b"ENDFILES\r\n"])
    clock = iter(range(20))
    monkeypatch.setattr(query_module.time, "monotonic", lambda: next(clock))
    with pytest.raises(query_module.QueryError, match="timed out"):
        query_module.soldat_info("localhost", 23083, timeout=3)
    assert sock.recv.call_count < 3
