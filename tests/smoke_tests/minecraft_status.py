import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import urllib.request


MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
BEDROCK_MAGIC = bytes.fromhex("00ffff00fefefefefdfdfdfd12345678")
BEDROCK_CLIENT_GUID = 0x1337C0DE12345678


def _installed_java_major():
    try:
        result = subprocess.run(
            ["java", "-version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    output = "\n".join(filter(None, [result.stdout, result.stderr]))
    match = re.search(r'version\s+"(\d+)(?:\.(\d+))?', output)
    if not match:
        return None

    major = int(match.group(1))
    if major == 1 and match.group(2):
        return int(match.group(2))
    return major


def _required_java_major(version_data):
    raw_major = version_data.get("javaVersion", {}).get("majorVersion")
    try:
        return int(raw_major)
    except (TypeError, ValueError):
        return None


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
            raise ConnectionError("Connection closed while reading VarInt")
        value = raw[0]
        result |= (value & 0x7F) << (7 * num_read)
        num_read += 1
        if num_read > 5:
            raise ValueError("VarInt too large")
        if value & 0x80 == 0:
            return result


def _status_ping(host, port, timeout=5):
    with socket.create_connection((host, port), timeout=timeout) as sock:
        handshake_data = b"".join(
            [
                _encode_varint(0),
                _encode_varint(760),
                _encode_varint(len(host)),
                host.encode("utf-8"),
                struct.pack(">H", port),
                _encode_varint(1),
            ]
        )
        sock.sendall(_encode_varint(len(handshake_data)) + handshake_data)
        sock.sendall(_encode_varint(1) + _encode_varint(0))
        _read_varint(sock)
        packet_id = _read_varint(sock)
        if packet_id != 0:
            raise ValueError(f"Unexpected status packet id: {packet_id}")
        payload_length = _read_varint(sock)
        payload = b""
        while len(payload) < payload_length:
            chunk = sock.recv(payload_length - len(payload))
            if not chunk:
                raise ConnectionError("Connection closed while reading status payload")
            payload += chunk
    return json.loads(payload.decode("utf-8"))


def _bedrock_ping(host, port, timeout=5):
    started = time.monotonic()
    ping_time = int(time.time() * 1000) & 0xFFFFFFFFFFFFFFFF
    payload = (
        b"\x01"
        + struct.pack(">Q", ping_time)
        + BEDROCK_MAGIC
        + struct.pack(">Q", BEDROCK_CLIENT_GUID)
    )

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(payload, (host, port))
        data, _ = sock.recvfrom(4096)

    if len(data) < 35:
        raise ValueError("Unexpected Bedrock pong length")
    if data[0] != 0x1C:
        raise ValueError(f"Unexpected Bedrock packet id: {data[0]}")
    if data[17:33] != BEDROCK_MAGIC:
        raise ValueError("Unexpected Bedrock pong magic")

    motd_length = struct.unpack_from(">H", data, 33)[0]
    motd_start = 35
    motd_end = motd_start + motd_length
    if len(data) < motd_end:
        raise ValueError("Truncated Bedrock pong payload")

    fields = data[motd_start:motd_end].decode("utf-8", errors="replace").split(";")
    if fields and fields[-1] == "":
        fields.pop()
    if len(fields) < 6:
        raise ValueError("Unexpected Bedrock pong structure")

    def _field(index, default=""):
        return fields[index] if index < len(fields) else default

    def _int_field(index):
        value = _field(index, "")
        return int(value) if value not in (None, "") else None

    return {
        "edition": _field(0),
        "name": _field(1),
        "protocol_version": _int_field(2),
        "version": _field(3),
        "players_online": _int_field(4),
        "players_max": _int_field(5),
        "server_id": _field(6),
        "map": _field(7),
        "gamemode": _field(8),
        "gamemode_numeric": _int_field(9),
        "port_v4": _int_field(10),
        "port_v6": _int_field(11),
        "latency_ms": round((time.monotonic() - started) * 1000.0, 1),
    }


def _wait_for_status(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            print(json.dumps(_status_ping(host, port), indent=2))
            return 0
        except Exception as ex:  # noqa: BLE001
            last_error = ex
            time.sleep(2)
    print(f"Minecraft server did not respond in time: {last_error}", file=sys.stderr)
    return 1


def _wait_for_bedrock_status(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            print(json.dumps(_bedrock_ping(host, port), indent=2))
            return 0
        except Exception as ex:  # noqa: BLE001
            last_error = ex
            time.sleep(2)
    print(f"Bedrock server did not respond in time: {last_error}", file=sys.stderr)
    return 1


def _wait_for_closed(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            _status_ping(host, port, timeout=2)
        except Exception:  # noqa: BLE001
            return 0
        time.sleep(2)
    print("Minecraft server still responds after stop timeout", file=sys.stderr)
    return 1


def _wait_for_bedrock_closed(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            _bedrock_ping(host, port, timeout=2)
        except Exception:  # noqa: BLE001
            return 0
        time.sleep(2)
    print("Bedrock server still responds after stop timeout", file=sys.stderr)
    return 1


def _latest_release():
    release_id = os.environ.get("ALPHAGSM_MINECRAFT_RELEASE_ID", "").strip()
    server_url = os.environ.get("ALPHAGSM_MINECRAFT_SERVER_URL", "").strip()
    if release_id or server_url:
        if not (release_id and server_url):
            print("Set both Minecraft fixture release ID and server URL", file=sys.stderr)
            return 1
        print(f"{release_id}\t{server_url}")
        return 0
    with urllib.request.urlopen(MANIFEST_URL, timeout=30) as response:
        manifest = json.loads(response.read().decode("utf-8"))

    installed_java_major = _installed_java_major()
    release_versions = [
        version for version in manifest["versions"] if version.get("type") == "release"
    ]

    selected_release = None
    for version in release_versions:
        with urllib.request.urlopen(version["url"], timeout=30) as response:
            version_data = json.loads(response.read().decode("utf-8"))

        server_download = version_data.get("downloads", {}).get("server")
        if not server_download:
            continue

        required_java_major = _required_java_major(version_data)
        if (
            installed_java_major is not None
            and required_java_major is not None
            and required_java_major > installed_java_major
        ):
            continue

        selected_release = (version["id"], server_download["url"])
        break

    if selected_release is None:
        latest_release_id = manifest["latest"]["release"]
        version_url = next(
            version["url"]
            for version in manifest["versions"]
            if version["id"] == latest_release_id
        )
        with urllib.request.urlopen(version_url, timeout=30) as response:
            version_data = json.loads(response.read().decode("utf-8"))
        selected_release = (latest_release_id, version_data["downloads"]["server"]["url"])

    release_id, server_url = selected_release
    print(f"{release_id}\t{server_url}")
    return 0


def main(argv):
    if len(argv) < 2:
        print(
            "usage: minecraft_status.py <latest-release|wait-for-status|wait-for-closed|wait-for-bedrock-status|wait-for-bedrock-closed> ...",
            file=sys.stderr,
        )
        return 2
    command = argv[1]
    if command == "latest-release":
        return _latest_release()
    if command == "wait-for-status":
        return _wait_for_status(argv[2], int(argv[3]), int(argv[4]))
    if command == "wait-for-closed":
        return _wait_for_closed(argv[2], int(argv[3]), int(argv[4]))
    if command == "wait-for-bedrock-status":
        return _wait_for_bedrock_status(argv[2], int(argv[3]), int(argv[4]))
    if command == "wait-for-bedrock-closed":
        return _wait_for_bedrock_closed(argv[2], int(argv[3]), int(argv[4]))
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
