"""Tests for utils.query — lightweight server query utilities."""

import socket

import pytest

import utils.query as query_module


# ---------------------------------------------------------------------------
# a2s_info
# ---------------------------------------------------------------------------

class _FakeUDPSocket:
    """Minimal socket stub for UDP tests."""

    def __init__(self, response=None, raise_on_send=None):
        self._response = response
        self._raise_on_send = raise_on_send

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def settimeout(self, t):
        pass

    def sendto(self, data, addr):
        if self._raise_on_send:
            raise self._raise_on_send

    def recvfrom(self, bufsize):
        return self._response, ("127.0.0.1", 27015)


def test_a2s_info_returns_response_on_valid_reply(monkeypatch):
    valid = b"\xff\xff\xff\xff\x49" + b"rest of payload"
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(response=valid),
    )
    result = query_module.a2s_info("127.0.0.1", 27015)
    assert result == valid


def test_a2s_info_raises_on_unexpected_header(monkeypatch):
    bad_response = b"\x00\x00\x00\x00garbage"
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(response=bad_response),
    )
    with pytest.raises(query_module.QueryError, match="Unexpected"):
        query_module.a2s_info("127.0.0.1", 27015)


def test_a2s_info_raises_on_socket_error(monkeypatch):
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(raise_on_send=OSError("timeout")),
    )
    with pytest.raises(query_module.QueryError, match="A2S query failed"):
        query_module.a2s_info("127.0.0.1", 27015)


# ---------------------------------------------------------------------------
# tcp_ping
# ---------------------------------------------------------------------------

def test_tcp_ping_returns_positive_latency(monkeypatch):
    class _FakeTCPSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            pass

    monkeypatch.setattr(
        query_module.socket,
        "create_connection",
        lambda addr, timeout: _FakeTCPSocket(),
    )
    ms = query_module.tcp_ping("127.0.0.1", 27015)
    assert ms >= 0.0


def test_tcp_ping_raises_on_connection_error(monkeypatch):
    def _fail(addr, timeout):
        raise OSError("refused")

    monkeypatch.setattr(query_module.socket, "create_connection", _fail)

    with pytest.raises(query_module.QueryError, match="TCP ping failed"):
        query_module.tcp_ping("127.0.0.1", 27015)


# ---------------------------------------------------------------------------
# parse_a2s_info
# ---------------------------------------------------------------------------

def _build_a2s_response(name="My Server", map_="de_dust2", folder="cstrike",
                         game="Counter-Strike", appid=240, players=5,
                         max_players=16, bots=0):
    """Build a minimal A2S_INFO response packet for testing."""
    import struct

    def cstr(s):
        return s.encode("utf-8") + b"\x00"

    payload = (
        b"\xff\xff\xff\xff\x49"   # header + type
        + b"\x11"                  # protocol version
        + cstr(name)
        + cstr(map_)
        + cstr(folder)
        + cstr(game)
        + struct.pack("<H", appid)
        + bytes([players, max_players, bots])
        + b"\x64\x6c\x00\x00"     # server_type, os, visibility, vac
    )
    return payload


def test_parse_a2s_info_extracts_all_fields():
    data = _build_a2s_response(
        name="Test Server", map_="de_nuke", folder="cstrike",
        game="CS:GO", appid=730, players=3, max_players=10, bots=1,
    )
    result = query_module.parse_a2s_info(data)
    assert result is not None
    assert result["name"] == "Test Server"
    assert result["map"] == "de_nuke"
    assert result["game"] == "CS:GO"
    assert result["appid"] == 730
    assert result["players"] == 3
    assert result["max_players"] == 10
    assert result["bots"] == 1


def test_parse_a2s_info_returns_none_on_truncated_data():
    result = query_module.parse_a2s_info(b"\xff\xff\xff\xff\x49\x11")
    assert result is None
