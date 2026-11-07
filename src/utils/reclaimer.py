"""Bounded Project Reclaimer WebSocket RCON (release RCON.md, protocol 1)."""

import base64
import hashlib
import json
import os
import socket
import struct
import time

from server.errors import ServerError

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_LIMIT = 16384


class _Connection:
    def __init__(self, sock, deadline):
        self.sock = sock
        self.deadline = deadline

    def _remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ServerError("Reclaimer RCON timed out")
        self.sock.settimeout(remaining)

    def read(self, size):
        result = bytearray()
        while len(result) < size:
            self._remaining()
            chunk = self.sock.recv(size - len(result))
            if not chunk:
                raise ServerError("Reclaimer RCON connection closed")
            result.extend(chunk)
        return bytes(result)

    def write(self, payload, opcode=1):
        if len(payload) > _LIMIT:
            raise ServerError("Reclaimer RCON message exceeds 16 KiB")
        mask = os.urandom(4)
        header = bytes([128 | opcode, 128 | len(payload)]) if len(payload) < 126 else (
            bytes([128 | opcode, 254]) + struct.pack("!H", len(payload)))
        masked = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
        self._remaining()
        self.sock.sendall(header + mask + masked)

    def send(self, record):
        self.write(json.dumps(record).encode("utf-8"))

    def receive(self):
        for _ in range(128):
            first, second = self.read(2)
            opcode = first & 15
            if first & 112 or not first & 128 or second & 128:
                raise ServerError("Reclaimer RCON returned unsupported WebSocket framing")
            length = second & 127
            if length == 126:
                length = struct.unpack("!H", self.read(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self.read(8))[0]
            if length > _LIMIT or (opcode >= 8 and length > 125):
                raise ServerError("Reclaimer RCON response exceeds its size limit")
            payload = self.read(length)
            if opcode == 9:
                self.write(payload, opcode=10)
                continue
            if opcode == 10:
                continue
            if opcode != 1:
                raise ServerError("Reclaimer RCON closed or returned a non-text message")
            try:
                result = json.loads(payload.decode("utf-8"))
            except (UnicodeError, ValueError) as exc:
                raise ServerError("Reclaimer RCON returned invalid JSON") from exc
            if not isinstance(result, dict):
                raise ServerError("Reclaimer RCON returned an invalid message")
            return result
        raise ServerError("Reclaimer RCON sent too many control frames")

    def upgrade(self, host, port):
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        address = f"[{host}]" if ":" in host else host
        request = (f"GET / HTTP/1.1\r\nHost: {address}:{port}\r\nUpgrade: websocket\r\n"
                   f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self._remaining()
        self.sock.sendall(request.encode("ascii"))
        header = bytearray()
        while not header.endswith(b"\r\n\r\n"):
            if len(header) >= 8192:
                raise ServerError("Reclaimer RCON upgrade headers exceed size limit")
            header.extend(self.read(1))
        lines = header.decode("ascii").split("\r\n")
        fields = {line.split(":", 1)[0].lower(): line.split(":", 1)[1].strip()
                  for line in lines[1:] if ":" in line}
        expected = base64.b64encode(hashlib.sha1((key + _GUID).encode("ascii")).digest()).decode("ascii")
        if (lines[0].split()[:2] != ["HTTP/1.1", "101"]
                or fields.get("sec-websocket-accept", "") != expected
                or fields.get("upgrade", "").lower() != "websocket"
                or "upgrade" not in {token.strip().lower() for token in fields.get("connection", "").split(",")}):
            raise ServerError("Reclaimer RCON WebSocket upgrade failed")


def command(host, port, password, text, timeout=5.0):
    """Authenticate and execute one command; never expose upstream auth errors."""
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        raise ServerError("Reclaimer RCON requires an 8 to 128 character password")
    if not isinstance(text, str) or not text.strip() or any(c in text for c in "\r\n\x00"):
        raise ServerError("Reclaimer RCON command must be one nonempty line")
    if any(c in str(host) for c in "\r\n\x00"):
        raise ServerError("Invalid Reclaimer RCON host")
    deadline = time.monotonic() + timeout
    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            connection = _Connection(sock, deadline)
            connection.upgrade(host, port)
            connection.send({"type": "auth", "password": password})
            auth = connection.receive()
            if auth.get("type") != "auth" or auth.get("ok") is not True or auth.get("protocol") != 1:
                raise ServerError("Reclaimer RCON authentication failed or protocol is unsupported")
            connection.send({"type": "command", "id": 1, "command": text})
            for _ in range(128):
                reply = connection.receive()
                if reply.get("type") == "event":
                    continue
                if reply.get("type") != "reply" or reply.get("id") != 1 or reply.get("ok") is not True:
                    raise ServerError("Reclaimer RCON command failed or reply did not match")
                return {**reply, "version": auth.get("version")}
            raise ServerError("Reclaimer RCON sent too many events without a reply")
    except (OSError, UnicodeError, ValueError) as exc:
        raise ServerError("Reclaimer RCON connection or protocol failed") from exc


def server_info(host, port, password, timeout=5.0):
    """Return only validated public status fields from the authenticated server."""
    reply = command(host, port, password, "status", timeout=timeout)
    record = reply.get("data")
    if not isinstance(record, dict):
        raise ServerError("Reclaimer RCON status is missing server metadata")
    players, maximum = record.get("players"), record.get("max_players")
    if any(not isinstance(value, int) or isinstance(value, bool) for value in (players, maximum)):
        raise ServerError("Reclaimer RCON status has invalid player counts")
    if not 0 <= players <= maximum <= 127 or maximum < 1:
        raise ServerError("Reclaimer RCON status has invalid player counts")
    result = {"players": players, "max_players": maximum}
    for source, destination in (("name", "name"), ("map", "map"), ("mode", "gamemode"), ("phase", "phase")):
        value = record.get(source)
        if not isinstance(value, str) or not value.strip() or len(value) > 1024:
            raise ServerError("Reclaimer RCON status has invalid text metadata")
        result[destination] = "".join(c for c in value if ord(c) >= 32)
    version = reply.get("version")
    if isinstance(version, str) and len(version) <= 128:
        result["version"] = "".join(c for c in version if ord(c) >= 32)
    return result
