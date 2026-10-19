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
        assert info["channels"] == [{"id": 1, "parent_id": 0, "order": 0, "name": "Lobby"}]
    assert len(sent) == 25
    assert all(command != "clientlist" for _, command in sent)
    assert all(connection.closed for connection in connections)
    assert all(later[0] - earlier[0] >= 0.3 for earlier, later in zip(sent, sent[1:]))


def _scripted_server(monkeypatch, *, channel_error=False, client_error=False):
    sent = []
    monkeypatch.setattr(query.time, "sleep", lambda _seconds: None)

    class ServerQueryConnection:
        def __init__(self):
            self.output = deque(b"TS3\nWelcome\n")

        def sendall(self, data):
            command = data.decode().strip()
            sent.append(command)
            if command == "channellist" and channel_error:
                self.output.extend(b"error id=2568 msg=insufficient\\sclient\\spermissions\n")
                return
            if command == "clientlist" and client_error:
                self.output.extend(b"error id=2568 msg=insufficient\\sclient\\spermissions\n")
                return
            if command == "serverinfo":
                self.output.extend(
                    b"virtualserver_name=Fixture virtualserver_clientsonline=3 "
                    b"virtualserver_queryclientsonline=1 virtualserver_maxclients=32 "
                    b"virtualserver_version=3.13.7\n"
                )
            elif command == "channellist":
                self.output.extend(
                    b"cid=1 pid=0 channel_order=0 channel_name=Lobby|"
                    b"cid=2 pid=1 channel_order=0 channel_name=Raid\n"
                )
            elif command == "clientlist":
                self.output.extend(
                    b"clid=1 cid=1 client_nickname=Ada client_type=0 "
                    b"client_unique_identifier=SECRET client_database_id=4 connection_client_ip=203.0.113.5|"
                    b"clid=2 cid=1 client_nickname=Query client_type=1 "
                    b"client_unique_identifier=QUERY connection_client_ip=198.51.100.5\n"
                )
            self.output.extend(b"error id=0 msg=ok\n")

        def recv(self, _size):
            return bytes([self.output.popleft()]) if self.output else b""

        def close(self):
            return None

    monkeypatch.setattr(query.socket, "create_connection", lambda *_args, **_kwargs: ServerQueryConnection())
    return sent


def test_detail_query_returns_parent_order_and_clients_without_identities(monkeypatch):
    sent = _scripted_server(monkeypatch)
    info = query.ts3_serverinfo("192.0.2.1", 10011, details=True)
    assert sent == ["use 1", "serverinfo", "channellist", "clientlist", "quit"]
    assert info["clients_online"] == 2 and info["query_clients"] == 1
    assert info["channels"] == [
        {"id": 1, "name": "Lobby", "parent_id": 0, "order": 0},
        {"id": 2, "name": "Raid", "parent_id": 1, "order": 0},
    ]
    assert info["clients"] == [
        {"nickname": "Ada", "channel_id": 1, "client_type": 0},
        {"nickname": "Query", "channel_id": 1, "client_type": 1},
    ]
    assert info["roster_error"] is False
    rendered = str(info)
    assert "SECRET" not in rendered and "203.0.113.5" not in rendered and "client_database_id" not in rendered


def test_refused_detail_list_keeps_the_count_and_marks_roster_error(monkeypatch):
    sent = _scripted_server(monkeypatch, channel_error=True)
    info = query.ts3_serverinfo("192.0.2.1", 10011, details=True)
    assert sent == ["use 1", "serverinfo", "channellist", "quit"]
    assert info["clients_online"] == 2 and info["channels"] == [] and info["clients"] == []
    assert info["roster_error"] is True


def test_refused_client_list_keeps_channels_and_marks_roster_error(monkeypatch):
    sent = _scripted_server(monkeypatch, client_error=True)
    info = query.ts3_serverinfo("192.0.2.1", 10011, details=True)
    assert "clientlist" in sent
    assert info["channels"][0]["name"] == "Lobby"
    assert info["clients"] == [] and info["roster_error"] is True
