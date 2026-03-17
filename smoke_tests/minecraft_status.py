import json
import socket
import struct
import sys
import time
import urllib.request


MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"


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


def _latest_release():
    with urllib.request.urlopen(MANIFEST_URL, timeout=30) as response:
        manifest = json.loads(response.read().decode("utf-8"))
    release_id = manifest["latest"]["release"]
    version_url = next(
        version["url"]
        for version in manifest["versions"]
        if version["id"] == release_id
    )
    with urllib.request.urlopen(version_url, timeout=30) as response:
        version_data = json.loads(response.read().decode("utf-8"))
    print(f"{release_id}\t{version_data['downloads']['server']['url']}")
    return 0


def main(argv):
    if len(argv) < 2:
        print("usage: minecraft_status.py <latest-release|wait-for-status|wait-for-closed> ...", file=sys.stderr)
        return 2
    command = argv[1]
    if command == "latest-release":
        return _latest_release()
    if command == "wait-for-status":
        return _wait_for_status(argv[2], int(argv[3]), int(argv[4]))
    if command == "wait-for-closed":
        return _wait_for_closed(argv[2], int(argv[3]), int(argv[4]))
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
