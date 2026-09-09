"""Source RCON query framing and response tests."""

import struct

import pytest

from utils import query


def _packet(request_id, packet_type, body):
    payload = struct.pack("<ii", request_id, packet_type) + body.encode() + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


class _Socket:
    def __init__(self, responses):
        self.responses = bytearray(b"".join(responses))
        self.sent = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def sendall(self, payload):
        self.sent.append(payload)

    def settimeout(self, timeout):
        self.timeout = timeout

    def recv(self, length):
        if not self.responses:
            return b""
        chunk = bytes(self.responses[:length])
        del self.responses[:length]
        return chunk


def test_source_rcon_list_players_authenticates_and_counts_players(monkeypatch):
    sock = _Socket([
        _packet(1, 0, ""),
        _packet(1, 2, ""),
        _packet(2, 0, "0. Alice, 123\n1. Bob, 456"),
    ])
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    result = query.source_rcon_info("127.0.0.1", 27020, "secret")

    assert result == {"players": 2}
    assert b"secret\x00\x00" in sock.sent[0]
    assert b"ListPlayers\x00\x00" in sock.sent[1]
    assert len(sock.sent) == 2


def test_source_rcon_list_players_understands_empty_server(monkeypatch):
    sock = _Socket([
        _packet(1, 2, ""),
        _packet(2, 0, "No Players Connected"),
    ])
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    assert query.source_rcon_info("host", 27020, "secret") == {"players": 0}


def test_source_rcon_rejects_failed_authentication(monkeypatch):
    sock = _Socket([_packet(-1, 2, "")])
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    with pytest.raises(query.QueryError, match="authentication failed"):
        query.source_rcon_info("host", 27020, "wrong")


def test_source_rcon_rejects_malformed_packet(monkeypatch):
    sock = _Socket([struct.pack("<i", 4) + b"bad!"])
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    with pytest.raises(query.QueryError, match="invalid packet length"):
        query.source_rcon_info("host", 27020, "secret")


def test_source_rcon_requires_password():
    with pytest.raises(query.QueryError, match="password is not configured"):
        query.source_rcon_info("host", 27020, "")


def test_source_rcon_aggregates_multipart_command_response(monkeypatch):
    sock = _Socket([
        _packet(1, 2, ""),
        _packet(2, 0, "0. Alice, 123\n"),
        _packet(2, 0, "1. Bob, 456\n"),
    ])
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    assert query.source_rcon_info("host", 27020, "secret") == {"players": 2}
    assert sock.responses == b""


def test_source_rcon_enforces_one_deadline_across_fragmented_reads(monkeypatch):
    response = [
        _packet(1, 2, ""),
        _packet(2, 0, "0. Alice, 123\n"),
    ]

    class SlowSocket(_Socket):
        def recv(self, length):
            return super().recv(1 if length else length)

    sock = SlowSocket(response)
    clock = iter(index * 0.3 for index in range(100))
    monkeypatch.setattr(query.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    with pytest.raises(query.QueryError, match="timed out"):
        query.source_rcon_info("host", 27020, "secret", timeout=1.0)


def test_source_rcon_rejects_oversized_multipart_response(monkeypatch):
    responses = [_packet(1, 2, "")]
    responses.extend(_packet(2, 0, "x" * 4096) for _ in range(256))
    responses.append(_packet(2, 0, "overflow"))
    sock = _Socket(responses)
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: sock)

    with pytest.raises(query.QueryError, match="1 MiB"):
        query.source_rcon_info("host", 27020, "secret")
