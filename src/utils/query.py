"""Lightweight server query utilities used by the 'query' command.

Provides query strategies:

* :func:`a2s_info` — Source/Steam A2S_INFO UDP query.
* :func:`quake_status` — Quake3/QFusion UDP getstatus query.
* :func:`quakeworld_status` — QuakeWorld UDP status query.
* :func:`quake2_status` — Quake II UDP status query.
* :func:`ut3_status` — Unreal Tournament 3 / Unreal3 GameSpy4 UDP probe.
* :func:`bedrock_info` — Minecraft Bedrock RakNet unconnected ping.
* :func:`slp_info` — Minecraft Server List Ping.
* :func:`ts3_serverinfo` — TeamSpeak 3 ServerQuery (telnet on port 10011).
* :func:`soldat_info` — classic Soldat file-server status query over TCP.
* :func:`source_rcon_info` — authenticated Source RCON ``ListPlayers`` query.
* :func:`http_json` — HTTP JSON endpoint query.
* :func:`udp_ping` — generic UDP reachability probe for silent listeners.
* :func:`tcp_ping` — TCP connect to prove a port is open.

Game modules may optionally define ``get_query_address(server)`` returning a
``(host, port, protocol)`` tuple where *protocol* is ``"a2s"``, ``"quake"``,
``"quakeworld"``, ``"quake2"``, ``"ut3"``, ``"bedrock"``, ``"ts3"``,
``"soldat"``, ``"source_rcon"``, ``"http_status"``, ``"udp"``, or ``"tcp"``.  When that hook
is absent the caller falls back to a TCP ping on the main port.
"""

import bz2
import json
import re
import socket
import struct
import time
import urllib.error
import urllib.request

__all__ = ["QueryError", "a2s_info", "parse_a2s_info", "quake_status", "quakeworld_status", "quake2_status", "ut3_status", "bedrock_info", "slp_info", "udp_ping", "tcp_ping",
           "ts3_serverinfo", "soldat_info", "source_rcon_info", "http_json"]

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
_UT3_QUERY_REQUEST = b"\xfe\xfd\x09\x00\x00\x00\x00"
_BEDROCK_UNCONNECTED_PING_ID = 0x01
_BEDROCK_UNCONNECTED_PONG_ID = 0x1C
_BEDROCK_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
_BEDROCK_CLIENT_GUID = 0x1337C0DE12345678


class QueryError(OSError):
    """Raised when a query attempt fails or returns an unexpected result."""


def soldat_info(host, port, timeout=5.0):
    """Read classic Soldat's fixed gamestat file from its TCP file port.

    Require the complete ENDFILES terminator plus player count and map fields.
    Limit the entire exchange to one deadline and at most 64 KiB of response;
    do not return player names or raw file contents.
    """

    deadline = time.monotonic() + timeout

    def remaining_time():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise QueryError("Soldat query timed out")
        return remaining

    data = bytearray()
    limit = 65536
    try:
        with socket.create_connection((host, int(port)), timeout=remaining_time()) as sock:
            sock.settimeout(remaining_time())
            sock.sendall(b"STARTFILES\r\nlogs/gamestat.txt\r\nENDFILES\r\n")
            while not data.endswith(b"ENDFILES\r\n"):
                if len(data) >= limit:
                    raise QueryError("Soldat response exceeds 64 KiB limit")
                sock.settimeout(remaining_time())
                chunk = sock.recv(min(4096, limit - len(data)))
                remaining_time()
                if not chunk:
                    raise QueryError("Soldat response ended before ENDFILES")
                data.extend(chunk)
                if len(data) > limit:
                    raise QueryError("Soldat response exceeds 64 KiB limit")
    except QueryError:
        raise
    except OSError as exc:
        raise QueryError("Soldat query failed: " + str(exc)) from exc

    # The file-transfer wrapper varies across classic versions. Validate the
    # documented gamestat fields without assuming an additional opening header.
    text = data.decode("utf-8", errors="replace")
    players = re.search(r"(?m)^[ \t]*Players:[ \t]*([0-9]+)[ \t]*\r?$", text)
    map_name = re.search(r"(?m)^[ \t]*Map:[ \t]*([^\r\n]+)", text)
    if not players or not map_name or not map_name[1].strip():
        raise QueryError("Soldat response is missing valid Players or Map fields")
    try:
        count = int(players[1])
    except ValueError as exc:
        raise QueryError("Soldat response has an invalid player count") from exc
    result = {"players": count, "map": map_name[1].strip()}
    gamemode = re.search(r"(?m)^[ \t]*Gamemode:[ \t]*([^\r\n]+)", text)
    if gamemode and gamemode[1].strip():
        result["gamemode"] = gamemode[1].strip()
    return result


def _source_rcon_info_once(host, port, password, timeout):
    """Run one bounded Source RCON authentication and command exchange.

    ARK: Survival Ascended exposes RCON rather than the Steam A2S endpoint used
    by Survival Evolved.  The response body is intentionally reduced to a
    count so player names and the configured password never reach manager
    output or diagnostic JSON. ASA omits the standard multipart sentinel, so
    fragments are collected until a short quiet window inside one deadline.
    """

    if not password:
        raise QueryError("Source RCON password is not configured")

    deadline = time.monotonic() + timeout

    def remaining_time():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise QueryError("Source RCON query timed out")
        return remaining

    def packet(request_id, packet_type, body):
        encoded = body.encode("utf-8")
        payload = struct.pack("<ii", request_id, packet_type) + encoded + b"\x00\x00"
        return struct.pack("<i", len(payload)) + payload

    def recv_exact(sock, length):
        chunks = bytearray()
        while len(chunks) < length:
            sock.settimeout(remaining_time())
            chunk = sock.recv(length - len(chunks))
            remaining_time()
            if not chunk:
                raise QueryError("Source RCON response ended unexpectedly")
            chunks.extend(chunk)
        return bytes(chunks)

    def recv_packet(sock, initial_header=b""):
        header = initial_header + recv_exact(sock, 4 - len(initial_header))
        size = struct.unpack("<i", header)[0]
        if size < 10 or size > 1024 * 1024:
            raise QueryError("Source RCON returned an invalid packet length")
        payload = recv_exact(sock, size)
        if not payload.endswith(b"\x00\x00"):
            raise QueryError("Source RCON returned malformed packet framing")
        request_id, packet_type = struct.unpack("<ii", payload[:8])
        body = payload[8:-2].decode("utf-8", errors="replace")
        return request_id, packet_type, body, size

    try:
        with socket.create_connection(
            (host, int(port)), timeout=remaining_time()
        ) as sock:
            sock.settimeout(remaining_time())
            sock.sendall(packet(1, 3, password))
            authenticated = False
            for _ in range(4):
                request_id, packet_type, _body, _size = recv_packet(sock)
                if request_id == -1:
                    raise QueryError("Source RCON authentication failed")
                if request_id == 1 and packet_type == 2:
                    authenticated = True
                    break
            if not authenticated:
                raise QueryError("Source RCON did not confirm authentication")

            sock.settimeout(remaining_time())
            sock.sendall(packet(2, 2, "ListPlayers"))
            response_parts = []
            response_size = 0
            for _ in range(4096):
                if response_parts:
                    sock.settimeout(min(0.05, remaining_time()))
                    try:
                        initial_header = sock.recv(4)
                    except socket.timeout:
                        break
                    remaining_time()
                    if not initial_header:
                        break
                else:
                    initial_header = b""
                request_id, packet_type, response_body, packet_size = recv_packet(
                    sock, initial_header
                )
                if request_id != 2 or packet_type != 0:
                    raise QueryError("Source RCON returned an unexpected command response")
                response_size += packet_size
                if response_size > 1024 * 1024:
                    raise QueryError("Source RCON response exceeds 1 MiB limit")
                response_parts.append(response_body)
            else:
                raise QueryError("Source RCON response has too many packets")
            body = "".join(response_parts)
    except QueryError:
        raise
    except OSError as exc:
        raise QueryError("Source RCON query failed: " + str(exc)) from exc

    if "no players connected" in body.lower():
        return {"players": 0}
    players = len(re.findall(r"(?m)^\s*\d+\.\s+", body))
    return {"players": players if players else None}


def source_rcon_info(
    host,
    port,
    password,
    timeout=5.0,
    *,
    retries=0,
    retry_delay=0.0,
):
    """Authenticate to Source RCON and return a bounded player count.

    Optional retries share the original total timeout. Only transient socket
    failures and deadline expiry are retried; invalid credentials, malformed
    framing, and unexpected protocol replies fail immediately.
    """

    deadline = time.monotonic() + timeout
    last_error = None
    for attempt in range(retries + 1):
        attempts_left = retries + 1 - attempt
        remaining = deadline - time.monotonic()
        delay_budget = retry_delay * (attempts_left - 1)
        attempt_timeout = (remaining - delay_budget) / attempts_left
        if attempt_timeout <= 0:
            break
        try:
            return _source_rcon_info_once(
                host,
                port,
                password,
                timeout=attempt_timeout,
            )
        except QueryError as exc:
            transient = isinstance(exc.__cause__, OSError) or "timed out" in str(
                exc
            ).lower()
            if not transient or attempt >= retries:
                raise
            last_error = exc
            remaining = deadline - time.monotonic()
            if remaining <= retry_delay:
                break
            time.sleep(retry_delay)

    raise QueryError("Source RCON query timed out after retries") from last_error


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


def bedrock_info(host, port, timeout=5.0):
    """Send a Bedrock RakNet unconnected ping and return server metadata.

    The returned dict contains at minimum: ``name`` (server MOTD line 1),
    ``map`` (MOTD line 2 / level name), ``players_online`` (int),
    ``players_max`` (int), ``version`` (str), and ``edition`` (str).

    Raises :class:`QueryError` on socket failure or malformed pong payloads.
    """

    started = time.monotonic()
    ping_time = int(time.time() * 1000) & 0xFFFFFFFFFFFFFFFF
    request = (
        bytes([_BEDROCK_UNCONNECTED_PING_ID])
        + struct.pack(">Q", ping_time)
        + _BEDROCK_MAGIC
        + struct.pack(">Q", _BEDROCK_CLIENT_GUID)
    )

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(request, (host, int(port)))
            data, _ = sock.recvfrom(4096)
    except OSError as exc:
        raise QueryError("Bedrock query failed: " + str(exc)) from exc

    if len(data) < 35:
        raise QueryError("Unexpected Bedrock pong length")
    if data[0] != _BEDROCK_UNCONNECTED_PONG_ID:
        raise QueryError("Unexpected Bedrock pong packet id")
    if data[17:33] != _BEDROCK_MAGIC:
        raise QueryError("Unexpected Bedrock pong magic")

    echoed_ping = struct.unpack_from(">Q", data, 1)[0]
    server_guid = struct.unpack_from(">Q", data, 9)[0]
    (payload_length,) = struct.unpack_from(">H", data, 33)
    payload_start = 35
    payload_end = payload_start + payload_length
    if len(data) < payload_end:
        raise QueryError("Truncated Bedrock pong payload")

    try:
        motd_fields = data[payload_start:payload_end].decode(
            "utf-8", errors="replace"
        ).split(";")
    except Exception as exc:  # noqa: BLE001
        raise QueryError("Failed to decode Bedrock pong payload: " + str(exc)) from exc

    if motd_fields and motd_fields[-1] == "":
        motd_fields.pop()
    if len(motd_fields) < 6:
        raise QueryError("Unexpected Bedrock pong structure")

    def _field(index, default=""):
        if index < len(motd_fields):
            return motd_fields[index]
        return default

    def _int_field(index, label):
        value = _field(index, "")
        if value in (None, ""):
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise QueryError(
                "Unexpected Bedrock pong {}: {!r}".format(label, value)
            ) from exc

    players_online = _int_field(4, "players_online")
    players_max = _int_field(5, "players_max")
    if players_online is None or players_max is None:
        raise QueryError("Unexpected Bedrock pong player counts")

    return {
        "edition": _field(0),
        "description": _field(1),
        "name": _field(1),
        "protocol_version": _int_field(2, "protocol_version"),
        "version": _field(3),
        "players_online": players_online,
        "players_max": players_max,
        "server_id": _field(6),
        "server_guid": server_guid,
        "map": _field(7),
        "gamemode": _field(8),
        "gamemode_numeric": _int_field(9, "gamemode_numeric"),
        "port_v4": _int_field(10, "port_v4"),
        "port_v6": _int_field(11, "port_v6"),
        "echoed_ping_time": echoed_ping,
        "latency_ms": round((time.monotonic() - started) * 1000.0, 1),
    }


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


def _format_http_host(host):
    """Return *host* formatted for use in an HTTP URL."""

    host = str(host)
    if ":" in host and not host.startswith("["):
        return "[{}]".format(host)
    return host


def http_json(host, port, path, timeout=5.0):
    """Fetch JSON from an HTTP endpoint and return the decoded object."""

    path = str(path)
    if not path.startswith("/"):
        path = "/" + path
    url = "http://{}:{}{}".format(_format_http_host(host), int(port), path)
    request = urllib.request.Request(url, headers={"User-Agent": "AlphaGSM"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            payload = response.read().decode(charset, errors="replace")
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise QueryError("HTTP JSON query failed for {}: {}".format(url, exc)) from exc
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise QueryError("HTTP JSON query failed for {}: invalid JSON response".format(url)) from exc


def udp_ping(host, port, timeout=2.0, payload=b"\x00"):
    """Probe a UDP port and return latency in milliseconds when reachable.

    This is a generic reachability check for servers that bind a UDP game port
    but do not expose a documented query protocol. After sending *payload* to a
    connected UDP socket, either a response packet or a read timeout counts as
    success. A timeout means the kernel did not receive ICMP port-unreachable
    during the probe window, which is sufficient to treat the port as open for
    AlphaGSM's local health checks. Explicit connection-refused errors are
    reported as failures.
    """
    start = time.time()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, int(port)))
            sock.send(payload)
            try:
                sock.recv(1)
            except socket.timeout:
                pass
    except OSError as exc:
        raise QueryError("UDP ping failed: " + str(exc)) from exc
    return (time.time() - start) * 1000.0


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
    text = data[4:].decode("utf-8", errors="replace")
    if not text.startswith("statusResponse\n"):
        raise QueryError("Unexpected Quake status response payload")
    # Response format: \xff\xff\xff\xffstatusResponse\n\cvars\n<player lines>
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


def quakeworld_status(host, port, timeout=2.0):
    """Send a QuakeWorld ``status`` UDP packet and parse the response."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(b"\xff\xff\xff\xffstatus\n", (host, int(port)))
            data, _ = sock.recvfrom(4096)
    except OSError as exc:
        raise QueryError("QuakeWorld status query failed: " + str(exc)) from exc
    if not data.startswith(b"\xff\xff\xff\xff"):
        raise QueryError("Unexpected QuakeWorld status response header")
    text = data[4:].decode("utf-8", errors="replace").rstrip("\x00")
    lines = [line for line in text.split("\n") if line.strip()]
    if not lines or not lines[0].startswith("n\\"):
        raise QueryError("Unexpected QuakeWorld status response payload")

    parts = lines[0][2:].split("\\")
    cvars = dict(zip(parts[::2], parts[1::2]))
    info = {
        "name": cvars.get("hostname", ""),
        "map": cvars.get("map", ""),
        "players": sum(1 for line in lines[1:] if line.strip()),
        "max_players": 0,
    }

    max_players = cvars.get("maxclients") or cvars.get("sv_maxclients")
    if max_players not in (None, ""):
        try:
            info["max_players"] = int(max_players)
        except ValueError:
            pass
    return info


def quake2_status(host, port, timeout=2.0):
    """Send a Quake II ``status`` UDP packet and parse the response."""

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(b"\xff\xff\xff\xffstatus\n", (host, int(port)))
            data, _ = sock.recvfrom(4096)
    except OSError as exc:
        raise QueryError("Quake II status query failed: " + str(exc)) from exc
    if not data.startswith(b"\xff\xff\xff\xff"):
        raise QueryError("Unexpected Quake II status response header")
    text = data[4:].decode("utf-8", errors="replace")
    if not text.startswith("print\n"):
        raise QueryError("Unexpected Quake II status response payload")
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


def ut3_status(host, port, timeout=2.0):
    """Send the Unreal3/GameSpy4 status probe used by UT3-style servers.

    The UT3/GameSpy4 query surface is enough for AlphaGSM to prove the query
    port is responding, but this helper intentionally does not attempt a full
    parser yet. It returns the raw response bytes when the server answers with
    a non-trivial packet.
    """

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(_UT3_QUERY_REQUEST, (host, int(port)))
            data, _ = sock.recvfrom(4096)
    except OSError as exc:
        raise QueryError("UT3 query failed: " + str(exc)) from exc
    if not data or len(data) < 5:
        raise QueryError("Unexpected UT3 response")
    return data


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

    Commands are paced below the default ten-commands-per-three-seconds flood
    limit, including the first command so consecutive CLI checks remain safe.

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
        # Docker queries need not originate from the exempt loopback address.
        # Include login and quit, and leave headroom above the 300ms minimum.
        time.sleep(0.35)
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
