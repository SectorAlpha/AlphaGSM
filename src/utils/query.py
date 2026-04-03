"""Lightweight server query utilities used by the 'query' command.

Provides query strategies:

* :func:`a2s_info` — Source/Steam A2S_INFO UDP query.
* :func:`quake_status` — Quake3/QFusion UDP getstatus query.
* :func:`slp_info` — Minecraft Server List Ping.
* :func:`ts3_serverinfo` — TeamSpeak 3 ServerQuery (telnet on port 10011).
* :func:`tcp_ping` — TCP connect to prove a port is open.

Game modules may optionally define ``get_query_address(server)`` returning a
``(host, port, protocol)`` tuple where *protocol* is ``"a2s"``, ``"quake"``,
``"ts3"``, or ``"tcp"``.  When that hook is absent the caller falls back to a
TCP ping on the main port.
"""

import bz2
import socket
import struct
import time

__all__ = ["QueryError", "a2s_info", "parse_a2s_info", "quake_status", "slp_info", "tcp_ping",
           "ts3_serverinfo"]

# Source/Steam A2S_INFO request payload and response headers.
_A2S_PAYLOAD = b"\x54Source Engine Query\x00"
_A2S_REQUEST = b"\xff\xff\xff\xff" + _A2S_PAYLOAD
# Simple-packet header (single UDP datagram).
_HEADER_SIMPLE = b"\xff\xff\xff\xff"
# Multi-packet header: response is split across several datagrams.
_HEADER_MULTI = b"\xfe\xff\xff\xff"
# Expected first byte of a valid A2S_INFO response after stripping the header.
_A2S_RESPONSE_TYPE = 0x49
# Challenge-response byte (0x41 = 'A').  Modern Steam servers may send this
# before the actual info, requiring the request to be re-sent with the
# 4-byte challenge appended.
_A2S_CHALLENGE_TYPE = 0x41


class QueryError(OSError):
    """Raised when a query attempt fails or returns an unexpected result."""


def _recv_a2s_packet(sock):
    """Receive one A2S UDP response, reassembling multi-packet fragments.

    Uses a 65535-byte buffer (maximum UDP payload) so that large single-packet
    responses are never silently truncated.  Multi-packet responses (indicated
    by the ``\\xfe\\xff\\xff\\xff`` header) are fully reassembled from all
    fragments before returning.

    Returns the raw payload bytes with the 4-byte simple-packet header stripped.
    """
    data = sock.recv(65535)
    if data[:4] == _HEADER_SIMPLE:
        return data[4:]
    if data[:4] == _HEADER_MULTI:
        # Fragment header layout (all little-endian):
        #   uint32  message_id   – high bit set when payload is bz2-compressed
        #   uint8   total        – total number of fragments
        #   uint8   frag_id      – zero-based index of this fragment
        #   uint16  mtu          – max fragment size (informational)
        # If compressed, two more fields follow before the payload:
        #   uint32  decompressed_size
        #   uint32  crc32
        _FRAG_HDR = struct.Struct("<IBBH")

        def _parse_fragment(raw):
            msg_id, total, frag_id, _ = _FRAG_HDR.unpack_from(raw)
            offset = _FRAG_HDR.size
            if msg_id & (1 << 15):  # compressed
                offset += 8  # skip decompressed_size + crc32
                payload = bz2.decompress(raw[offset:])
            else:
                payload = raw[offset:]
            return total, frag_id, payload

        total, frag_id, payload = _parse_fragment(data[4:])
        fragments = {frag_id: payload}
        while len(fragments) < total:
            pkt = sock.recv(65535)
            _, fid, fpayload = _parse_fragment(pkt[4:])
            fragments[fid] = fpayload
        reassembled = b"".join(fragments[i] for i in range(total))
        if reassembled[:4] == _HEADER_SIMPLE:
            reassembled = reassembled[4:]
        return reassembled
    raise QueryError("A2S query failed: Unexpected response header " + repr(data[:4]))


def a2s_info(host, port, timeout=2.0, phase2_timeout=None):
    """Send an A2S_INFO packet to *host*:*port* and return the raw response.

    Handles the modern Steam challenge-response handshake: if the server
    responds with a challenge (header byte 0x41) the request is re-sent with
    the 4-byte challenge appended and the final info response is returned.
    Multi-packet (fragmented) responses are automatically reassembled.

    *timeout* is the socket timeout for Phase 1 (waiting for the initial
    challenge or response).  *phase2_timeout* is the socket timeout for
    Phase 2 (waiting for the info response after sending the challenge);
    defaults to *timeout* when not specified.  Use a longer *phase2_timeout*
    when querying Source/SRCDS servers in hibernation mode: Phase 1 catches
    the server during a brief wake window, while Phase 2 must wait an entire
    hibernation cycle for the server to wake again.

    Raises :class:`QueryError` on timeout, socket error, or an unexpected
    response header.
    """
    if phase2_timeout is None:
        phase2_timeout = timeout
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(_A2S_REQUEST, (host, int(port)))
            data = _recv_a2s_packet(sock)
            # Some modern servers respond with a challenge before sending info.
            if len(data) >= 5 and data[0] == _A2S_CHALLENGE_TYPE:
                challenge = data[1:5]
                sock.settimeout(phase2_timeout)
                sock.sendto(_A2S_REQUEST + challenge, (host, int(port)))
                data = _recv_a2s_packet(sock)
    except OSError as exc:
        raise QueryError("A2S query failed: " + str(exc)) from exc
    if not data or data[0] != _A2S_RESPONSE_TYPE:
        raise QueryError("Unexpected A2S response header")
    return b"\xff\xff\xff\xff" + data


def _read_cstring(data, pos):
    """Read a null-terminated UTF-8 string from *data* at *pos*.

    Returns ``(string, next_pos)``.
    """
    end = data.index(b"\x00", pos)
    return data[pos:end].decode("utf-8", errors="replace"), end + 1


def parse_a2s_info(data):
    """Parse a raw A2S_INFO response into a dict.

    Returns a dict with keys ``name``, ``map``, ``folder``, ``game``,
    ``appid``, ``players``, ``max_players``, and ``bots``, or ``None``
    if parsing fails (e.g. truncated or malformed packet).
    """
    try:
        pos = 5  # skip 4-byte FF prefix + 0x49 type byte
        pos += 1  # protocol version byte
        name, pos = _read_cstring(data, pos)
        map_, pos = _read_cstring(data, pos)
        folder, pos = _read_cstring(data, pos)
        game, pos = _read_cstring(data, pos)
        (appid,) = struct.unpack_from("<H", data, pos)
        pos += 2
        players = data[pos]
        max_players = data[pos + 1]
        bots = data[pos + 2]
        return {
            "name": name,
            "map": map_,
            "folder": folder,
            "game": game,
            "appid": appid,
            "players": players,
            "max_players": max_players,
            "bots": bots,
        }
    except Exception:  # noqa: BLE001
        return None


def slp_info(host, port, timeout=5.0):
    """Send a Minecraft Server List Ping to *host*:*port* and return a dict.

    The returned dict contains at minimum: ``description`` (str),
    ``players_online`` (int), ``players_max`` (int), ``version`` (str).
    When online players are listed, ``player_names`` (list[str]) is also
    included.

    Raises :class:`QueryError` on connection failure or unexpected response.
    """
    import json as _json

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

    def _read_varint(sock):
        num_read = 0
        result = 0
        while True:
            raw = sock.recv(1)
            if not raw:
                raise QueryError("Connection closed while reading VarInt")
            byte = raw[0]
            result |= (byte & 0x7F) << (7 * num_read)
            num_read += 1
            if num_read > 5:
                raise QueryError("VarInt too large")
            if (byte & 0x80) == 0:
                return result

    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            host_bytes = host.encode("utf-8")
            handshake = b"".join([
                _encode_varint(0),        # packet id 0 = handshake
                _encode_varint(760),      # protocol version (servers accept any)
                _encode_varint(len(host_bytes)),
                host_bytes,
                struct.pack(">H", int(port)),
                _encode_varint(1),        # next state = status
            ])
            sock.sendall(_encode_varint(len(handshake)) + handshake)
            sock.sendall(_encode_varint(1) + _encode_varint(0))  # status request
            _read_varint(sock)   # packet length (ignored)
            packet_id = _read_varint(sock)
            if packet_id != 0:
                raise QueryError(f"Unexpected SLP packet id: {packet_id}")
            payload_length = _read_varint(sock)
            payload = bytearray()
            while len(payload) < payload_length:
                chunk = sock.recv(payload_length - len(payload))
                if not chunk:
                    raise QueryError("Connection closed while reading SLP payload")
                payload.extend(chunk)
    except QueryError:
        raise
    except OSError as exc:
        raise QueryError("SLP query failed: " + str(exc)) from exc

    try:
        raw = _json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise QueryError("Failed to parse SLP JSON: " + str(exc)) from exc

    try:
        desc = raw.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("text", "")
        result = {
            "description": str(desc),
            "players_online": int(raw["players"]["online"]),
            "players_max": int(raw["players"]["max"]),
            "version": str(raw["version"]["name"]),
        }
        sample = raw.get("players", {}).get("sample", [])
        if sample:
            result["player_names"] = [p["name"] for p in sample if "name" in p]
        return result
    except (KeyError, TypeError, ValueError) as exc:
        raise QueryError("Unexpected SLP response structure: " + str(exc)) from exc


def quake_status(host, port, timeout=2.0):
    """Send a Quake3/QFusion ``getstatus`` UDP packet and parse the response.

    Used by servers based on the Quake3/QFusion engine (e.g. Warfork/Warsow).
    Returns a dict with keys ``name``, ``map``, ``players``, and
    ``max_players``.  Raises :class:`QueryError` if no valid response arrives.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(b"\xff\xff\xff\xffgetstatus\n", (host, int(port)))
            data, _ = sock.recvfrom(4096)
    except OSError as exc:
        raise QueryError("Quake status query failed: " + str(exc)) from exc
    if not data.startswith(b"\xff\xff\xff\xff"):
        raise QueryError("Unexpected Quake status response header")
    # Response format: \xff\xff\xff\xffstatusResponse\n\cvars\n<player lines>
    text = data[4:].decode("utf-8", errors="replace")
    lines = text.split("\n")
    info = {"name": "", "map": "", "players": 0, "max_players": 0}
    if len(lines) >= 2:
        parts = lines[1].strip("\\").split("\\")
        cvars = dict(zip(parts[::2], parts[1::2]))

        for key in ("sv_hostname", "hostname", "si_name"):
            value = cvars.get(key, "")
            if value:
                info["name"] = value
                break

        for key in ("mapname", "map"):
            value = cvars.get(key, "")
            if value:
                info["map"] = value
                break

        for key in ("sv_maxclients", "maxclients", "si_maxPlayers"):
            value = cvars.get(key)
            if value in (None, ""):
                continue
            try:
                parsed = int(value)
            except ValueError:
                continue
            if parsed > 0:
                info["max_players"] = parsed
                break
        info["players"] = sum(1 for line in lines[2:] if line.strip())
    return info


def tcp_ping(host, port, timeout=2.0):
    """Open a TCP connection to *host*:*port* and immediately close it.

    Returns the round-trip time in milliseconds.  Raises :class:`QueryError`
    on failure.
    """
    t0 = time.monotonic()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            pass
    except OSError as exc:
        raise QueryError("TCP ping failed: " + str(exc)) from exc
    return (time.monotonic() - t0) * 1000


def _ts3_unescape(value):
    """Decode a TeamSpeak 3 ServerQuery escaped string."""
    return (
        value
        .replace("\\s", " ")
        .replace("\\p", "|")
        .replace("\\n", "\n")
        .replace("\\/", "/")
        .replace("\\\\", "\\")
    )


def ts3_serverinfo(host, port, timeout=5.0, login=None):
    """Connect to a TeamSpeak 3 ServerQuery interface and return server info.

    Opens a raw TCP session to the TS3 ServerQuery port (default 10011),
    sends ``serverinfo`` and ``channellist``, then parses and returns a dict
    with the following keys:

    * ``name`` — virtual server name (str)
    * ``clients_online`` — current number of connected clients (int)
    * ``max_clients`` — maximum allowed clients (int)
    * ``uptime`` — server uptime in seconds (int)
    * ``platform`` — host platform string (str)
    * ``version`` — server software version (str)
    * ``channels`` — list of channel dicts, each with ``id`` (int) and
      ``name`` (str)

    Optional *login* is a ``(username, password)`` tuple.  When provided a
    ``login`` command is sent before ``use 1``, which is required for
    TeamSpeak 3 server 3.13+ where anonymous ServerQuery connections no longer
    receive elevated permissions.

    Raises :class:`QueryError` on connection failure, unexpected banner, or
    malformed response.
    """
    try:
        conn = socket.create_connection((host, int(port)), timeout=timeout)
    except OSError as exc:
        raise QueryError("TS3 ServerQuery connection failed: " + str(exc)) from exc

    def _recvline():
        """Read bytes until a newline (LF), decode, and strip whitespace."""
        buf = bytearray()
        while True:
            chunk = conn.recv(1)
            if not chunk:
                raise QueryError("TS3 ServerQuery: connection closed unexpectedly")
            buf.extend(chunk)
            if buf.endswith(b"\n"):
                return buf.decode("utf-8", errors="replace").strip()

    def _send(cmd):
        conn.sendall((cmd + "\n").encode("utf-8"))

    def _read_until_ok():
        """Collect lines until an 'error id=0' line; return non-error lines."""
        lines = []
        while True:
            line = _recvline()
            if line.startswith("error "):
                if "id=0" not in line:
                    raise QueryError("TS3 ServerQuery error: " + line)
                return lines
            if line:
                lines.append(line)

    def _parse_kv(line):
        """Parse a TS3 key=value space-separated line into a dict."""
        result = {}
        for token in line.split(" "):
            if "=" in token:
                k, _, v = token.partition("=")
                result[k] = _ts3_unescape(v)
            elif token:
                result[token] = ""
        return result

    try:
        # Expect the TS3 welcome banner: "TS3" on first line.
        banner = _recvline()
        if not banner.startswith("TS3"):
            raise QueryError("TS3 ServerQuery: unexpected banner: " + banner)
        # Read and discard the second welcome line (hostname info).
        _recvline()

        # Authenticate if credentials were supplied (required for TS3 3.13+).
        if login is not None:
            _send("login %s %s" % (login[0], login[1]))
            _read_until_ok()

        # Select virtual server 1 (required by TS3 3.13+ for per-server queries).
        _send("use 1")
        _read_until_ok()

        # Retrieve virtual server info.
        _send("serverinfo")
        si_lines = _read_until_ok()

        # Retrieve channel list.
        _send("channellist")
        cl_lines = _read_until_ok()

        _send("quit")
    finally:
        conn.close()

    # Parse serverinfo response.
    if not si_lines:
        raise QueryError("TS3 ServerQuery: empty serverinfo response")
    si = _parse_kv(si_lines[0])

    def _int(d, k):
        try:
            return int(d.get(k, 0))
        except (ValueError, TypeError):
            return 0

    result = {
        "name": si.get("virtualserver_name", ""),
        "clients_online": _int(si, "virtualserver_clientsonline"),
        "max_clients": _int(si, "virtualserver_maxclients"),
        "uptime": _int(si, "virtualserver_uptime"),
        "platform": si.get("virtualserver_platform", ""),
        "version": si.get("virtualserver_version", ""),
    }

    # Parse channellist response (entries separated by "|").
    channels = []
    if cl_lines:
        for entry in cl_lines[0].split("|"):
            ch = _parse_kv(entry)
            try:
                channels.append({"id": int(ch.get("cid", 0)), "name": ch.get("channel_name", "")})
            except (ValueError, TypeError):
                pass
    result["channels"] = channels

    return result
