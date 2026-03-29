"""Lightweight server query utilities used by the 'query' command.

Provides two probing strategies:

* :func:`a2s_info` — Source/Steam A2S_INFO UDP query.
* :func:`tcp_ping` — TCP connect to prove a port is open.

Game modules may optionally define ``get_query_address(server)`` returning a
``(host, port, protocol)`` tuple where *protocol* is ``"a2s"`` or ``"tcp"``.
When that hook is absent the caller falls back to a TCP ping on the main port.
"""

import socket
import time

__all__ = ["QueryError", "a2s_info", "tcp_ping"]

# Source/Steam A2S_INFO challenge bytes and expected response header.
_A2S_REQUEST = b"\xff\xff\xff\xffTSource Engine Query\x00"
_A2S_HEADER = b"\xff\xff\xff\xff\x49"


class QueryError(OSError):
    """Raised when a query attempt fails or returns an unexpected result."""


def a2s_info(host, port, timeout=2.0):
    """Send an A2S_INFO packet to *host*:*port* and return the raw response.

    Raises :class:`QueryError` on timeout, socket error, or an unexpected
    response header.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(_A2S_REQUEST, (host, int(port)))
            data, _ = sock.recvfrom(4096)
    except OSError as exc:
        raise QueryError("A2S query failed: " + str(exc)) from exc
    if not data.startswith(_A2S_HEADER):
        raise QueryError("Unexpected A2S response header")
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
