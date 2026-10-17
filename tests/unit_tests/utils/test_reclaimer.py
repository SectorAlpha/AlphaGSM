"""A real local WebSocket peer exercises the documented RCON exchange."""

import base64
import hashlib
import json
import socket
import struct
import threading
import time
from contextlib import contextmanager

import pytest

from server import ServerError


def read_exact(sock, size):
    result = b""
    while len(result) < size:
        chunk = sock.recv(size - len(result))
        assert chunk
        result += chunk
    return result


def receive(sock):
    first, second = read_exact(sock, 2)
    assert first == 0x81 and second & 128
    length = second & 127
    if length == 126:
        length = struct.unpack("!H", read_exact(sock, 2))[0]
    mask = read_exact(sock, 4)
    payload = read_exact(sock, length)
    return json.loads(bytes(value ^ mask[i % 4] for i, value in enumerate(payload)))


def send(sock, value):
    data = json.dumps(value).encode()
    header = bytes([0x81, len(data)]) if len(data) < 126 else b"\x81\x7e" + struct.pack("!H", len(data))
    sock.sendall(header + data)


@contextmanager
def peer(*, reject=False, bad_status=False, wrong_id=False):
    errors = []
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(3)

        def serve():
            try:
                with listener.accept()[0] as sock:
                    sock.settimeout(3)
                    header = b""
                    while not header.endswith(b"\r\n\r\n"):
                        header += read_exact(sock, 1)
                    key = next(line.split(":", 1)[1].strip() for line in header.decode().splitlines()
                               if line.lower().startswith("sec-websocket-key:"))
                    accept = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()
                    sock.sendall(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                                  'Sec-WebSocket-Accept: ' + accept + '\r\n\r\n').encode())
                    assert receive(sock) == {"type": "auth", "password": "private-password"}
                    send(sock, {"type": "auth", "ok": not reject, "protocol": 1, "version": "0.9.18", "error": "private-password"})
                    if reject:
                        return
                    request = receive(sock)
                    assert request["command"] == "status"
                    send(sock, {"type": "event", "event": "chat", "text": "private player info"})
                    send(sock, {"type": "reply", "id": 999 if wrong_id else request["id"], "ok": True,
                                "data": {"name": "Friends", "map": "Guardian", "mode": "Slayer", "phase": "lobby",
                                         "players": -1 if bad_status else 0, "max_players": 16,
                                         "private": "private-password"}})
            except Exception as exc:  # surfaced in the test thread
                errors.append(exc)

        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            yield listener.getsockname()[1]
        finally:
            thread.join(4)
            assert not thread.is_alive()
            if errors:
                raise errors[0]


def test_authenticated_status_filters_private_fields_and_ignores_events():
    from utils import reclaimer
    with peer() as port:
        result = reclaimer.server_info("127.0.0.1", port, "private-password")
    assert result == {"name": "Friends", "map": "Guardian", "gamemode": "Slayer", "phase": "lobby",
                      "players": 0, "max_players": 16, "version": "0.9.18"}


@pytest.mark.parametrize("options", [{"reject": True}, {"bad_status": True}, {"wrong_id": True}])
def test_rejects_invalid_or_unauthenticated_metadata_without_secrets(options):
    from utils import reclaimer
    with peer(**options) as port, pytest.raises(ServerError) as error:
        reclaimer.server_info("127.0.0.1", port, "private-password")
    assert "private-password" not in str(error.value)


def test_upgrade_rejects_wrong_case_in_accept_hash(monkeypatch):
    from utils import reclaimer
    monkeypatch.setattr(reclaimer.os, "urandom", lambda size: b"x" * size)
    key = base64.b64encode(b"x" * 16).decode()
    expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode()

    class FakeSocket:
        data = ('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                'Sec-WebSocket-Accept: ' + expected.swapcase() + '\r\n\r\n').encode()

        def settimeout(self, value):
            pass

        def sendall(self, value):
            pass

        def recv(self, size):
            value, self.data = self.data[:size], self.data[size:]
            return value

    with pytest.raises(ServerError, match="upgrade"):
        reclaimer._Connection(FakeSocket(), time.monotonic() + 2).upgrade("localhost", 49176)
