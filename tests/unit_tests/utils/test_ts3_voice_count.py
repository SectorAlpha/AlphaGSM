"""TeamSpeak voice counts omit the ServerQuery connection that reads them."""

from collections import deque

import pytest

from utils import query
from utils.query import QueryError


def _connection(serverinfo):
    class ServerQueryConnection:
        def __init__(self):
            self.output = deque(b"TS3\nWelcome\n")

        def sendall(self, data):
            if data.startswith(b"serverinfo"):
                self.output.extend(serverinfo)
            elif data.startswith(b"channellist"):
                self.output.extend(b"cid=1 channel_name=Lobby\n")
            self.output.extend(b"error id=0 msg=ok\n")

        def recv(self, _size):
            return bytes([self.output.popleft()]) if self.output else b""

        def close(self):
            return None

    return ServerQueryConnection


def _query(monkeypatch, serverinfo):
    monkeypatch.setattr(query.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: _connection(serverinfo)())
    return query.ts3_serverinfo("192.0.2.1", 10011)


def test_the_query_connection_is_not_a_voice_client(monkeypatch):
    info = _query(
        monkeypatch,
        b"virtualserver_name=Sector\\sAlpha "
        b"virtualserver_clientsonline=1 "
        b"virtualserver_queryclientsonline=1 "
        b"virtualserver_maxclients=64 "
        b"virtualserver_version=3.12.1\n",
    )
    assert info["clients_online"] == 0
    assert info["query_clients"] == 1
    assert info["max_clients"] == 64
    assert info["name"] == "Sector Alpha"


def test_voice_clients_remain_after_query_clients_are_removed(monkeypatch):
    info = _query(
        monkeypatch,
        b"virtualserver_name=Lobby virtualserver_clientsonline=4 virtualserver_queryclientsonline=1\n",
    )
    assert info["clients_online"] == 3
    assert info["query_clients"] == 1


def test_a_query_client_count_above_the_online_count_is_rejected(monkeypatch):
    with pytest.raises(QueryError, match="query client count"):
        _query(
            monkeypatch,
            b"virtualserver_name=Lobby virtualserver_clientsonline=1 virtualserver_queryclientsonline=2\n",
        )
