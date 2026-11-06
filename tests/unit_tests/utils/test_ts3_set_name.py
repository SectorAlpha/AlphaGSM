"""A local ServerQuery login can rename the virtual server without printing the password."""

from collections import deque

import pytest

from utils.query import QueryError, ts3_escape, ts3_set_name


def test_server_name_edit_logs_in_and_escapes_the_previous_name(monkeypatch):
    sent = []

    class Connection:
        def __init__(self):
            self.output = deque(b"TS3\nWelcome\n")

        def sendall(self, data):
            sent.append(data.decode().strip())
            self.output.extend(b"error id=0 msg=ok\n")

        def recv(self, _size):
            return bytes([self.output.popleft()]) if self.output else b""

        def close(self):
            pass

    monkeypatch.setattr("utils.query.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("utils.query.socket.create_connection", lambda *args, **kwargs: Connection())
    ts3_set_name("127.0.0.1", 10011, "Sector Alpha", login=("serveradmin", "secret value"))
    assert sent[0] == "login serveradmin secret\\svalue"
    assert sent[1] == "use 1"
    assert sent[2] == "serveredit virtualserver_name=Sector\\sAlpha"
    assert sent[3] == "quit"
    assert ts3_escape("a/b|c") == "a\\/b\\pc"
    with pytest.raises(QueryError):
        ts3_set_name("127.0.0.1", 10011, "x" * 65, login=("serveradmin", "secret"))
    with pytest.raises(QueryError):
        ts3_set_name("127.0.0.1", 10011, "Voice", login=None)
