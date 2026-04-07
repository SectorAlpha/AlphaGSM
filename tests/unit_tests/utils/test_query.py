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

    def connect(self, addr):
        pass

    def send(self, data):
        if self._raise_on_send:
            raise self._raise_on_send

    def recv(self, bufsize):
        return self._response

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


def test_udp_ping_returns_positive_latency_on_silent_listener(monkeypatch):
    class _SilentUDPSocket(_FakeUDPSocket):
        def recv(self, bufsize):
            raise socket.timeout()

    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _SilentUDPSocket(),
    )

    ms = query_module.udp_ping("127.0.0.1", 27015)
    assert ms >= 0.0


def test_udp_ping_raises_on_socket_error(monkeypatch):
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(raise_on_send=OSError("refused")),
    )

    with pytest.raises(query_module.QueryError, match="UDP ping failed"):
        query_module.udp_ping("127.0.0.1", 27015)


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


# ---------------------------------------------------------------------------
# slp_info
# ---------------------------------------------------------------------------

def _build_slp_response(
    description="A Minecraft Server",
    players_online=3,
    players_max=20,
    version_name="1.20.1",
    sample=None,
):
    """Build a minimal Minecraft SLP JSON status payload as bytes."""
    import json, struct

    payload_dict = {
        "description": {"text": description},
        "players": {"online": players_online, "max": players_max},
        "version": {"name": version_name, "protocol": 763},
    }
    if sample is not None:
        payload_dict["players"]["sample"] = sample
    payload_bytes = json.dumps(payload_dict).encode("utf-8")

    def _encode_varint(value):
        buf = bytearray()
        while True:
            temp = value & 0x7F
            value >>= 7
            if value != 0:
                temp |= 0x80
            buf.append(temp)
            if value == 0:
                return bytes(buf)

    # packet: length(varint) + packet_id(varint 0) + string_length(varint) + payload
    inner = _encode_varint(0) + _encode_varint(len(payload_bytes)) + payload_bytes
    packet = _encode_varint(len(inner)) + inner
    return packet


def test_slp_info_extracts_all_fields(monkeypatch):
    import socket as _socket

    packet = _build_slp_response(
        description="Hello World",
        players_online=5,
        players_max=25,
        version_name="1.20.4",
        sample=[{"name": "Alice", "id": "uuid1"}, {"name": "Bob", "id": "uuid2"}],
    )

    class _FakeSock:
        def __init__(self):
            self._data = packet
            self._pos = 0
            self._sent = []

        def sendall(self, data):
            self._sent.append(data)

        def recv(self, n):
            chunk = self._data[self._pos:self._pos + n]
            self._pos += n
            return chunk

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    monkeypatch.setattr(
        _socket,
        "create_connection",
        lambda addr, timeout=None: _FakeSock(),
    )

    result = query_module.slp_info("127.0.0.1", 25565)
    assert result["description"] == "Hello World"
    assert result["players_online"] == 5
    assert result["players_max"] == 25
    assert result["version"] == "1.20.4"
    assert result["player_names"] == ["Alice", "Bob"]


def test_slp_info_raises_on_connection_error(monkeypatch):
    import socket as _socket

    monkeypatch.setattr(
        _socket,
        "create_connection",
        lambda addr, timeout=None: (_ for _ in ()).throw(OSError("refused")),
    )
    with pytest.raises(query_module.QueryError, match="SLP query failed"):
        query_module.slp_info("127.0.0.1", 25565)


# ---------------------------------------------------------------------------
# quake_status
# ---------------------------------------------------------------------------


def test_quake_status_parses_q3_style_cvars(monkeypatch):
    payload = (
        b"\xff\xff\xff\xffstatusResponse\n"
        b"\\sv_hostname\\AlphaGSM Q3\\mapname\\q3dm17\\sv_maxclients\\16\n"
        b"0 50 \"Player1\"\n"
    )
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(response=payload),
    )

    result = query_module.quake_status("127.0.0.1", 27960)

    assert result == {
        "name": "AlphaGSM Q3",
        "map": "q3dm17",
        "players": 1,
        "max_players": 16,
    }


def test_quake_status_parses_legacy_cvar_aliases(monkeypatch):
    payload = (
        b"\xff\xff\xff\xffstatusResponse\n"
        b"\\hostname\\AlphaGSM Q2\\map\\q2dm1\\maxclients\\12\n"
    )
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(response=payload),
    )

    result = query_module.quake_status("127.0.0.1", 27910)

    assert result == {
        "name": "AlphaGSM Q2",
        "map": "q2dm1",
        "players": 0,
        "max_players": 12,
    }


def test_quake_status_parses_q4_style_cvar_aliases(monkeypatch):
    payload = (
        b"\xff\xff\xff\xffstatusResponse\n"
        b"\\si_name\\AlphaGSM Q4\\map\\q4dm1\\si_maxPlayers\\8\n"
    )
    monkeypatch.setattr(
        query_module.socket,
        "socket",
        lambda *a, **kw: _FakeUDPSocket(response=payload),
    )

    result = query_module.quake_status("127.0.0.1", 28004)

    assert result == {
        "name": "AlphaGSM Q4",
        "map": "q4dm1",
        "players": 0,
        "max_players": 8,
    }
