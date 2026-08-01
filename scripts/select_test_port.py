#!/usr/bin/env python3
"""Select test ports that remain stable during network-heavy setup work."""

from pathlib import Path
import secrets
import socket
import sys


DEFAULT_EPHEMERAL_MIN = 32768
DEFAULT_EPHEMERAL_MAX = 60999
DEFAULT_TEST_PORT_MIN = 10000
DEFAULT_TEST_PORT_MAX = 29999
DEFAULT_RANGE_PATH = Path("/proc/sys/net/ipv4/ip_local_port_range")
PROBE_HOSTS = ("127.0.0.1", "0.0.0.0")


def candidate_base_ports(
    count,
    min_port=DEFAULT_TEST_PORT_MIN,
    max_port=DEFAULT_TEST_PORT_MAX,
    ephemeral_range=None,
):
    """Return candidate group bases outside the ephemeral range."""

    count = int(count)
    min_port = int(min_port)
    max_port = int(max_port)
    if count <= 0:
        raise ValueError("Port group size must be positive")
    if min_port <= 0 or max_port > 65535 or min_port > max_port:
        raise ValueError("Port range must be within 1-65535")
    if ephemeral_range is None:
        ephemeral_range = read_ephemeral_port_range()
    ephemeral_min, ephemeral_max = map(int, ephemeral_range)
    max_base = max_port - count + 1
    return [
        base
        for base in range(min_port, max_base + 1)
        if base + count - 1 < ephemeral_min or base > ephemeral_max
    ]


def read_ephemeral_port_range(path=DEFAULT_RANGE_PATH):
    """Return the host's configured ephemeral port range."""

    try:
        values = Path(path).read_text(encoding="ascii").split()
        if len(values) != 2:
            raise ValueError("Expected exactly two port values")
        minimum, maximum = map(int, values)
        if minimum <= 0 or maximum > 65535 or minimum > maximum:
            raise ValueError("Invalid ephemeral port range")
        return minimum, maximum
    except (OSError, TypeError, ValueError):
        return DEFAULT_EPHEMERAL_MIN, DEFAULT_EPHEMERAL_MAX


def port_free_for_both(port):
    """Return whether TCP and UDP can bind *port* on loopback and wildcard."""

    for socktype in (socket.SOCK_STREAM, socket.SOCK_DGRAM):
        for host in PROBE_HOSTS:
            with socket.socket(socket.AF_INET, socktype) as probe:
                try:
                    # This wildcard bind is a short-lived, non-listening collision
                    # probe; the context manager closes it before this returns.
                    # codeql[py/bind-socket-all-network-interfaces]
                    probe.bind((host, port))
                except OSError:
                    return False
    return True


def pick_free_port_group(
    count,
    min_port=DEFAULT_TEST_PORT_MIN,
    max_port=DEFAULT_TEST_PORT_MAX,
    ephemeral_range=None,
    start_index=None,
    port_is_free=None,
):
    """Return the base of a free consecutive TCP+UDP port group."""

    candidates = candidate_base_ports(
        count,
        min_port=min_port,
        max_port=max_port,
        ephemeral_range=ephemeral_range,
    )
    if not candidates:
        raise RuntimeError("No non-ephemeral candidate port groups are available")
    if port_is_free is None:
        port_is_free = port_free_for_both
    if start_index is None:
        start_index = secrets.randbelow(len(candidates))
    start_index = int(start_index) % len(candidates)
    ordered_candidates = candidates[start_index:] + candidates[:start_index]
    count = int(count)
    for base in ordered_candidates:
        if all(port_is_free(port) for port in range(base, base + count)):
            return base
    raise RuntimeError(
        f"Could not find a free non-ephemeral TCP+UDP port group of size {count}"
    )


def main(argv=None):
    """Print a free test port-group base for shell smoke runners."""

    args = sys.argv[1:] if argv is None else list(argv)
    if len(args) != 1:
        print("Usage: select_test_port.py <group-size>", file=sys.stderr)
        return 2
    try:
        port = pick_free_port_group(int(args[0]))
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
