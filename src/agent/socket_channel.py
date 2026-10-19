# pylint: disable=unidiomatic-typecheck
"""One outbound WebSocket to the agent API. The game host does not listen."""

import base64
import hashlib
import json
import os
import socket
import ssl
import time
from urllib.parse import urlsplit

from .config import canonical_agent_origin
from .transport import AgentLimit, TransportError

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_MAX_FRAME = 65536


class SocketError(OSError):
    """The outbound socket failed before a command could run."""


class SocketClosed(SocketError):
    def __init__(self, code=1000):
        super().__init__("WebSocket closed")
        self.code = code


def _token(credential, session_id):
    if type(credential) is not dict or type(session_id) is not str:
        raise SocketError("Invalid agent credential")
    key_id, secret = credential.get("key_id"), credential.get("secret")
    if type(key_id) is not str or type(secret) is not str:
        raise SocketError("Invalid agent credential")
    token = key_id + "." + secret
    if any(ord(char) <= 32 or ord(char) > 126 for char in token + session_id):
        raise SocketError("Invalid agent credential")
    return token


def _accept_value(nonce):
    digest = hashlib.sha1((nonce + _GUID).encode("ascii"), usedforsecurity=False).digest()
    return base64.b64encode(digest).decode("ascii")


def encode_frame(payload, opcode=0x1):
    if type(payload) is not bytes:
        payload = json.dumps(payload, separators=(",", ":")).encode()
    if len(payload) > _MAX_FRAME:
        raise SocketError("WebSocket frame exceeds byte limit")
    header = bytearray((0x80 | opcode,))
    length = len(payload)
    if length < 126:
        header.append(0x80 | length)
    else:
        header.append(0x80 | 126)
        header.extend(length.to_bytes(2, "big"))
    mask = os.urandom(4)
    header.extend(mask)
    header.extend(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return bytes(header)


def _pop_frame(buffer):
    if len(buffer) < 2:
        return None
    first, second = buffer[0], buffer[1]
    if second & 0x80:
        raise SocketError("Server frame was masked")
    length = second & 0x7F
    offset = 2
    if length == 126:
        if len(buffer) < 4:
            return None
        length = int.from_bytes(buffer[2:4], "big")
        offset = 4
    elif length == 127:
        raise SocketError("WebSocket frame exceeds byte limit")
    if length > _MAX_FRAME or len(buffer) < offset + length:
        if length > _MAX_FRAME:
            raise SocketError("WebSocket frame exceeds byte limit")
        return None
    if not first & 0x80:
        raise SocketError("Fragmented WebSocket frames are not accepted")
    payload = bytes(buffer[offset:offset + length])
    del buffer[:offset + length]
    return first & 0x0F, payload


class SocketChannel:
    def __init__(self, origin, credential, session_id, *, context=None, connector=None):
        selected = canonical_agent_origin(origin)
        parsed = urlsplit(selected)
        self.endpoint = (parsed.hostname, parsed.port or 443)
        self.credential = credential
        self.session_id = session_id
        self.context = context
        self.connector = connector
        self._sock = None
        self._buffer = bytearray()

    def __enter__(self):
        self._sock = self._open()
        try:
            self._handshake()
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False

    def _open(self):
        host, port = self.endpoint
        if self.connector is not None:
            return self.connector()
        raw = socket.create_connection((host, port), timeout=10)
        context = self.context or ssl.create_default_context()
        try:
            return context.wrap_socket(raw, server_hostname=host)
        except Exception:
            raw.close()
            raise

    def _handshake(self):
        host, port = self.endpoint
        token = _token(self.credential, self.session_id)
        nonce = base64.b64encode(os.urandom(16)).decode("ascii")
        authority = "[" + host + "]" if ":" in host else host
        if port != 443:
            authority = authority + ":" + str(port)
        request = "\r\n".join((
            "GET /v1/agent/session HTTP/1.1",
            "Host: " + authority,
            "Upgrade: websocket",
            "Connection: Upgrade",
            "Sec-WebSocket-Key: " + nonce,
            "Sec-WebSocket-Version: 13",
            "Authorization: Bearer " + token,
            "X-Agent-Session: " + self.session_id,
            "",
            "",
        ))
        self._sock.sendall(request.encode("ascii"))
        head, extra = self._read_head()
        lines = head.split("\r\n")
        if len(lines[0].split(" ")) < 2 or lines[0].split(" ")[1] != "101":
            raise SocketError("WebSocket handshake rejected")
        headers = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            name, value = line.split(":", 1)
            headers[name.strip().lower()] = value.strip()
        if headers.get("sec-websocket-accept") != _accept_value(nonce):
            raise SocketError("WebSocket handshake rejected")
        self._buffer.extend(extra)

    def _read_head(self):
        data = bytearray()
        while b"\r\n\r\n" not in data:
            if len(data) > 8192:
                raise SocketError("WebSocket handshake exceeds byte limit")
            chunk = self._sock.recv(1024)
            if not chunk:
                raise SocketError("WebSocket handshake failed")
            data.extend(chunk)
        head, _, extra = bytes(data).partition(b"\r\n\r\n")
        return head.decode("ascii", "replace"), extra

    def send(self, payload):
        if self._sock is None:
            raise SocketError("WebSocket closed")
        self._sock.sendall(encode_frame(payload))

    def recv(self, timeout):
        deadline = time.monotonic() + timeout
        while True:
            message = self._next_message()
            if message is not None:
                return message
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            self._sock.settimeout(remaining)
            try:
                chunk = self._sock.recv(4096)
            except socket.timeout:
                return None
            if not chunk:
                raise SocketClosed(1006)
            self._buffer.extend(chunk)

    def _next_message(self):
        while True:
            frame = _pop_frame(self._buffer)
            if frame is None:
                return None
            opcode, payload = frame
            if opcode == 0x9:
                self.send_raw(encode_frame(payload, opcode=0xA))
                continue
            if opcode == 0x8:
                code = int.from_bytes(payload[:2], "big") if len(payload) >= 2 else 1000
                if code == 4429:
                    raise AgentLimit("Live agent cap reached")
                raise SocketClosed(code)
            if opcode == 0xA:
                continue
            if opcode != 0x1:
                raise SocketError("Unsupported WebSocket frame")
            try:
                message = json.loads(payload.decode())
            except (UnicodeError, json.JSONDecodeError):
                raise SocketError("Invalid WebSocket message") from None
            if type(message) is not dict:
                raise SocketError("Invalid WebSocket message")
            return message

    def send_raw(self, payload):
        if self._sock is None:
            raise SocketError("WebSocket closed")
        self._sock.sendall(payload)

    def close(self):
        sock, self._sock = self._sock, None
        if sock is None:
            return
        try:
            sock.sendall(encode_frame((1000).to_bytes(2, "big"), opcode=0x8))
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass
