import socket
import struct
import sys
import time


INFO_REQUEST = b"\xFF\xFF\xFF\xFFTSource Engine Query\x00"


def _query_info(host, port, timeout=5):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(INFO_REQUEST, (host, port))
        payload, _ = sock.recvfrom(4096)
        if payload[4:5] == b"A":
            challenge = payload[5:9]
            sock.sendto(INFO_REQUEST + challenge, (host, port))
            payload, _ = sock.recvfrom(4096)
        if payload[:4] != b"\xFF\xFF\xFF\xFF":
            raise ValueError("Invalid Source query header")
        if payload[4:5] != b"I":
            raise ValueError(f"Unexpected Source query type: {payload[4:5]!r}")
        return payload


def _wait_for_status(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        try:
            payload = _query_info(host, port)
            print(f"Received {len(payload)} bytes from Source query")
            return 0
        except Exception as ex:  # noqa: BLE001
            last_error = ex
            time.sleep(2)
    print(f"TF2 server did not respond to Source query in time: {last_error}", file=sys.stderr)
    return 1


def _wait_for_closed(host, port, timeout_seconds):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            _query_info(host, port, timeout=2)
        except Exception:  # noqa: BLE001
            return 0
        time.sleep(2)
    print("TF2 server still responds after stop timeout", file=sys.stderr)
    return 1


def main(argv):
    if len(argv) < 2:
        print("usage: source_status.py <wait-for-status|wait-for-closed> <host> <port> <timeout>", file=sys.stderr)
        return 2
    command = argv[1]
    if command == "wait-for-status":
        return _wait_for_status(argv[2], int(argv[3]), int(argv[4]))
    if command == "wait-for-closed":
        return _wait_for_closed(argv[2], int(argv[3]), int(argv[4]))
    print(f"unknown command: {command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
