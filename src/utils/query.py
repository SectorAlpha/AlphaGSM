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
* :func:`squad_rcon_info` — Squad's native RCON ``ShowServerInfo`` JSON query.
* :func:`http_json` — HTTP JSON endpoint query.
* :func:`udp_ping` — generic UDP reachability probe for silent listeners.
* :func:`tcp_ping` — TCP connect to prove a port is open.
* :func:`terraria_info` — framed Terraria connection handshake.

Game modules may optionally define ``get_query_address(server)`` returning a
``(host, port, protocol)`` tuple where *protocol* is ``"a2s"``, ``"quake"``,
``"quakeworld"``, ``"quake2"``, ``"ut3"``, ``"bedrock"``, ``"ts3"``,
``"soldat"``, ``"source_rcon"``, ``"squad_rcon"``, ``"http_status"``, ``"terraria"``,
``"udp"``, or ``"tcp"``. When that hook is absent the caller falls back to a
TCP ping on the main port.
"""

# pylint: disable=too-many-lines,unidiomatic-typecheck

import bz2
import zlib
import json
import re
import socket
import struct
import time
import urllib.error
import urllib.request

__all__ = ["QueryError", "a2s_info", "parse_a2s_info", "quake_status", "quakeworld_status", "quake2_status", "ut3_status", "bedrock_info", "slp_info", "udp_ping", "tcp_ping", "terraria_info",
           "ts3_serverinfo", "soldat_info", "source_rcon_info", "squad_rcon_info", "http_json"]

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


def _source_rcon_command_once(host, port, password, timeout, command):
    """Run one bounded Source RCON authentication and command exchange.

    Responses remain private to protocol-specific parsers, which expose only
    approved public metadata. Fragments are collected until a short quiet
    window inside one deadline for engines without the multipart sentinel.
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
            sock.sendall(packet(2, 2, command))
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

    return body


def _source_rcon_info_once(host, port, password, timeout):
    """Reduce ARK's native ListPlayers response to a public player count."""
    body = _source_rcon_command_once(host, port, password, timeout, 'ListPlayers')
    if "no players connected" in body.lower():
        return {"players": 0}
    players = len(re.findall(r"(?m)^\s*\d+\.\s+", body))
    return {"players": players if players else None}


def squad_rcon_info(host, port, password, timeout=5.0):
    """Read real Squad game state while discarding credentials and other fields."""
    deadline = time.monotonic() + timeout
    body = _source_rcon_command_once(host, port, password, timeout, 'ShowServerInfo')
    try:
        record = json.loads(body)
        if not isinstance(record, dict):
            raise ValueError('Expected an object')
        values = [record['PlayerCount_I'], record['MaxPlayers']]
        if any(isinstance(value, bool) or not re.fullmatch(r'[0-9]{1,4}', str(value))
               for value in values):
            raise ValueError('Invalid population')
        players, maximum = map(int, values)
        if not 0 <= players <= maximum <= 1000 or maximum == 0:
            raise ValueError('Invalid population bounds')
        result = {'players': players, 'max_players': maximum}
        for native, public in [('MapName_s', 'map'), ('ServerName_s', 'name'),
                               ('GameMode_s', 'gamemode'), ('GameVersion_s', 'version')]:
            value = record.get(native)
            if value is not None:
                if not isinstance(value, str) or len(value) > 1024:
                    raise ValueError('Invalid text metadata')
                result[public] = ''.join(character for character in value if ord(character) >= 32)
    except (KeyError, TypeError, ValueError) as exc:
        raise QueryError('Squad RCON returned invalid server metadata') from exc
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise QueryError('Squad RCON query timed out')
    current = _source_rcon_command_once(host, port, password, remaining, 'ShowCurrentMap')
    match = re.fullmatch(r'Current level is ([^,\r\n]{1,256}), layer is ([^,\r\n]{1,256}), factions [^\r\n]{1,512}',
                         current.strip())
    if not match or any(not value.strip() or value.strip().lower() == 'unknown'
                        or any(ord(character) < 32 for character in value)
                        for value in match.groups()):
        raise QueryError('Squad RCON did not confirm a loaded map and layer')
    result.update(map=match[1].strip(), layer=match[2].strip())
    return result


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


def _remaining(deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise QueryError("Query total deadline exceeded")
    return remaining


def _recv_a2s_packet(sock, deadline=None, max_bytes=256 * 1024):
    """Validate Source split framing before bounded aggregate decompression."""
    deadline = deadline if deadline is not None else time.monotonic() + 2.0
    fragments = {}
    identity = None
    total_size = 0
    expected_size = checksum = None
    for _ in range(16):
        sock.settimeout(_remaining(deadline))
        data = sock.recv(65535)
        _remaining(deadline)
        if data[:4] == _HEADER_SIMPLE and not fragments:
            if len(data) > max_bytes:
                raise QueryError("A2S response exceeds byte limit")
            return data[4:]
        if data[:4] != _HEADER_MULTI or len(data) < 12:
            raise QueryError("A2S query failed: Unexpected response header")
        message_id, total, index, mtu = struct.unpack_from("<IBBH", data, 4)
        if not 1 <= total <= 16 or index >= total or not 1 <= mtu <= 65535:
            raise QueryError("Invalid A2S fragment header")
        key = (message_id, total, mtu)
        if identity is not None and identity != key:
            raise QueryError("Mismatched A2S fragment identity")
        identity = key
        if index in fragments:
            raise QueryError("Duplicate A2S fragment")
        payload = data[12:]
        if message_id & 0x80000000 and index == 0:
            if len(payload) < 8:
                raise QueryError("Missing A2S compression metadata")
            expected_size, checksum = struct.unpack_from("<II", payload)
            if expected_size > max_bytes:
                raise QueryError("A2S decompressed size exceeds byte limit")
            payload = payload[8:]
        total_size += len(payload)
        if total_size > max_bytes or len(payload) > mtu:
            raise QueryError("A2S fragments exceed byte limit")
        fragments[index] = payload
        if len(fragments) == total:
            assembled = b"".join(fragments[i] for i in range(total))
            if message_id & 0x80000000:
                try:
                    decompressor = bz2.BZ2Decompressor()
                    assembled = decompressor.decompress(assembled, max_length=max_bytes + 1)
                    if (len(assembled) > max_bytes or not decompressor.eof or decompressor.unused_data
                            or len(assembled) != expected_size or zlib.crc32(assembled) != checksum):
                        raise QueryError("Invalid bounded A2S compressed response")
                except (OSError, EOFError, ValueError) as exc:
                    raise QueryError("Invalid A2S compression") from exc
            _remaining(deadline)
            return assembled[4:] if assembled[:4] == _HEADER_SIMPLE else assembled
    raise QueryError("Too many A2S fragments")


def a2s_info(host, port, timeout=2.0, phase2_timeout=None):
    """Query one connected UDP endpoint with a total monotonic byte/time budget.

    Explicit longer phase-two budgets support local hibernating Source servers.
    Public callers supply only timeout, giving a five-second total budget.
    """
    deadline = time.monotonic() + (timeout + phase2_timeout if phase2_timeout is not None else timeout)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(min(timeout, _remaining(deadline)))
            sock.connect((host, int(port)))
            sock.sendto(_A2S_REQUEST, (host, int(port)))
            data = _recv_a2s_packet(sock, deadline)
            if data and data[0] == _A2S_CHALLENGE_TYPE:
                if len(data) != 5:
                    raise QueryError("Invalid A2S challenge")
                sock.settimeout(_remaining(deadline))
                sock.sendto(_A2S_REQUEST + data[1:5], (host, int(port)))
                data = _recv_a2s_packet(sock, deadline)
    except OSError as exc:
        raise QueryError("A2S query failed: " + str(exc)) from exc
    if not data or data[0] != _A2S_RESPONSE_TYPE:
        raise QueryError("Unexpected A2S response header")
    return _HEADER_SIMPLE + data


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


def _encode_varint(value):
    buf = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        buf.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(buf)


def _json_depth_bounded(payload, maximum=16):
    depth = 0
    in_string = escaped = False
    for char in payload:
        if in_string:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                in_string = False
        elif char == 34:
            in_string = True
        elif char in (91, 123):
            depth += 1
            if depth > maximum:
                raise QueryError("SLP JSON nesting exceeds limit")
        elif char in (93, 125):
            depth -= 1


def slp_info(host, port, timeout=5.0, *, virtual_host=None, max_bytes=256 * 1024):
    """Read exactly one bounded SLP frame under a total deadline.

    A public worker connects to a validated numeric host and separately supplies
    the original hostname for Minecraft's virtual-host handshake.
    """
    deadline = time.monotonic() + timeout

    def recv_exact(sock, count):
        result = bytearray()
        while len(result) < count:
            sock.settimeout(_remaining(deadline))
            chunk = sock.recv(count - len(result))
            _remaining(deadline)
            if not chunk:
                raise QueryError("Connection closed while reading SLP payload")
            result.extend(chunk)
        return bytes(result)

    def read_varint(read):
        value = 0
        for i in range(5):
            byte = read(1)[0]
            if i == 4 and byte > 7:
                raise QueryError("VarInt too large")
            value |= (byte & 127) << (i * 7)
            if not byte & 128:
                return value
        raise QueryError("VarInt too large")

    host_bytes = (virtual_host if virtual_host is not None else host).encode("utf-8")
    if not 1 <= len(host_bytes) <= 255:
        raise QueryError("Invalid SLP virtual host")
    try:
        with socket.create_connection((host, int(port)), timeout=_remaining(deadline)) as sock:
            sock.settimeout(_remaining(deadline))
            handshake = (b"\x00" + _encode_varint(760) + _encode_varint(len(host_bytes)) + host_bytes
                         + struct.pack(">H", int(port)) + b"\x01")
            sock.sendall(_encode_varint(len(handshake)) + handshake)
            sock.settimeout(_remaining(deadline))
            sock.sendall(b"\x01\x00")
            size = read_varint(lambda n: recv_exact(sock, n))
            if not 3 <= size <= max_bytes:
                raise QueryError("SLP packet length exceeds limit")
            frame = recv_exact(sock, size)
    except OSError as exc:
        raise QueryError("SLP query failed: " + str(exc)) from exc
    position = 0

    def frame_read(n):
        nonlocal position
        if position + n > len(frame):
            raise QueryError("Truncated SLP frame")
        part = frame[position:position + n]
        position += n
        return part

    if read_varint(frame_read) != 0:
        raise QueryError("Unexpected SLP packet id")
    size = read_varint(frame_read)
    if size != len(frame) - position:
        raise QueryError("Invalid SLP string framing")
    payload = frame_read(size)
    _json_depth_bounded(payload)
    try:
        raw = json.loads(payload.decode("utf-8"))
        players, capacity = raw["players"]["online"], raw["players"]["max"]
        if type(players) is not int or type(capacity) is not int or not 0 <= players <= capacity <= 100000:
            raise QueryError("Invalid SLP player counts")
        desc = raw.get("description", "")
        if isinstance(desc, dict):
            desc = desc.get("text", "")
        result = {"description": desc if type(desc) is str else "", "players_online": players,
                      "players_max": capacity, "version": raw["version"]["name"]}
        sample = raw["players"].get("sample", [])
        if sample:
            result["player_names"] = [p["name"] for p in sample[:256]
                                      if isinstance(p, dict) and isinstance(p.get("name"), str)]
        _remaining(deadline)
        return result
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise QueryError("Unexpected SLP response structure") from exc


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


def terraria_info(host, port, timeout=2.0):
    """Probe a Terraria listener with a complete connection handshake.

    Terraria treats every accepted TCP socket as a game client. Opening and
    immediately closing one can crash current vanilla servers in
    ``DebugNetworkStream``. Send a correctly framed connection request with a
    deliberately unsupported protocol version, then read the complete server
    response before closing. A disconnect, slot assignment, or password
    challenge proves that the listener speaks Terraria's native protocol.
    """

    version = b"Terraria0"
    request = (
        struct.pack("<HB", 4 + len(version), 1)
        + bytes((len(version),))
        + version
    )

    def recv_exact(sock, length):
        data = bytearray()
        while len(data) < length:
            chunk = sock.recv(length - len(data))
            if not chunk:
                raise QueryError("Terraria response ended unexpectedly")
            data.extend(chunk)
        return bytes(data)

    try:
        with socket.create_connection((host, int(port)), timeout=timeout) as sock:
            sock.settimeout(timeout)
            sock.sendall(request)
            header = recv_exact(sock, 3)
            packet_length, response_type = struct.unpack("<HB", header)
            if packet_length < 3 or packet_length > 65535:
                raise QueryError("Terraria returned an invalid packet length")
            recv_exact(sock, packet_length - 3)
    except QueryError:
        raise
    except OSError as exc:
        raise QueryError("Terraria query failed: " + str(exc)) from exc

    responses = {
        2: "disconnect",
        3: "continue",
        37: "password",
    }
    if response_type not in responses:
        raise QueryError(
            "Terraria returned unexpected response type {}".format(response_type)
        )
    return {"response": responses[response_type]}


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
