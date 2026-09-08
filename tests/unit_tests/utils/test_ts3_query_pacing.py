"""Sequential TeamSpeak health checks respect the native ServerQuery flood limit."""

from collections import deque

from utils import query


def test_repeated_authenticated_queries_stay_below_flood_limit(monkeypatch):
    now = [0.0]
    sent = []
    connections = []
    monkeypatch.setattr(query.time, "monotonic", lambda: now[0])
    monkeypatch.setattr(query.time, "sleep", lambda seconds: now.__setitem__(0, now[0] + seconds))

    class ServerQueryConnection:
        def __init__(self):
            self.output = deque(b"TS3\nWelcome\n")
            self.closed = False

        def sendall(self, data):
            sent.append((now[0], data.decode().strip()))
            if sum(timestamp > now[0] - 3 for timestamp, _command in sent) > 10:
                self.output.extend(b"error id=524 msg=client\\sis\\sflooding\n")
                return
            if data.startswith(b"serverinfo"):
                self.output.extend(b"virtualserver_name=Fixture virtualserver_clientsonline=1\n")
            elif data.startswith(b"channellist"):
                self.output.extend(b"cid=1 channel_name=Lobby\n")
            self.output.extend(b"error id=0 msg=ok\n")

        def recv(self, _size):
            return bytes([self.output.popleft()]) if self.output else b""

        def close(self):
            self.closed = True

    def connect(*_args, **_kwargs):
        connection = ServerQueryConnection()
        connections.append(connection)
        return connection

    monkeypatch.setattr(query.socket, "create_connection", connect)
    # The CI sequence: readiness, query, text info, JSON info, detailed info.
    for _ in range(5):
        info = query.ts3_serverinfo("192.0.2.1", 10011, login=("serveradmin", "fixture"))
        assert info["name"] == "Fixture"
        assert info["channels"] == [{"id": 1, "name": "Lobby"}]
    assert len(sent) == 25
    assert all(connection.closed for connection in connections)
    assert all(later[0] - earlier[0] >= 0.3 for earlier, later in zip(sent, sent[1:]))
