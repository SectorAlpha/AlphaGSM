"""Bounded public-address suggestions without credentials, proxies or redirects."""

import ipaddress
import queue
import socket
import ssl
import threading
import time
import urllib.request

from .transport import NoRedirect
from .http_deadline import DeadlineBudget, DeadlineHTTPSHandler

LOOKUP_URL = "https://api.ipify.org"
LOOKUP_TIMEOUT = 5
LOOKUP_BYTES = 64
_LOOKUP_LOCK = threading.Lock()


def global_ip(value):
    """Accept a numerical, globally routable unicast address only."""
    if not isinstance(value, str) or "%" in value:
        return None
    try:
        address = ipaddress.ip_address(value)
        if address.is_global and not address.is_multicast and not address.is_reserved:
            return str(address)
    except ValueError:
        pass
    return None


def routing_ip():
    """Inspect the outbound route without sending application data."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
            route.settimeout(1)
            route.connect(("1.1.1.1", 80))
            return global_ip(route.getsockname()[0])
    except OSError:
        return None


class _LookupBudget(DeadlineBudget):
    def __init__(self):
        super().__init__(LOOKUP_TIMEOUT, family=socket.AF_INET)


def _lookup_exchange(budget):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(), DeadlineHTTPSHandler(budget),
    )
    request = urllib.request.Request(LOOKUP_URL, headers={"Accept": "text/plain"}, method="GET")
    with opener.open(request, timeout=budget.remaining()) as response:
        if response.geturl() != LOOKUP_URL:
            return None
        parts = bytearray()
        while response.fp is not None:
            response.fp.raw._sock.settimeout(budget.remaining())  # pylint: disable=protected-access
            chunk = response.read1(LOOKUP_BYTES + 1 - len(parts))
            parts.extend(chunk)
            if len(parts) > LOOKUP_BYTES:
                return None
            if not chunk:
                break
        value = global_ip(parts.decode("ascii").strip())
        return value if value is not None and ipaddress.ip_address(value).version == 4 else None


def lookup_ip():
    """Bound all phases, close active I/O at expiry, and return no offline hint."""
    # At most one fallback worker may exist, even if system DNS is stuck across
    # repeated report renewals. Explicit IP expectations remain usable.
    if not _LOOKUP_LOCK.acquire(blocking=False):
        return None
    budget = _LookupBudget()
    result = queue.Queue(maxsize=1)

    def exchange():
        try:
            result.put(_lookup_exchange(budget))
        except Exception:  # Cancellation may interrupt any urllib/TLS operation.
            result.put(None)
        finally:
            _LOOKUP_LOCK.release()

    worker = threading.Thread(target=exchange, daemon=True, name="alphagsm-public-ip")
    worker.start()
    try:
        return result.get(timeout=budget.remaining())
    except (queue.Empty, TimeoutError):
        return None
    finally:
        budget.cancel()
        # Active network I/O is now closed. A stalled system DNS resolver is the
        # only worker that may linger, without sockets or permission to connect.
        worker.join(timeout=max(0, budget.deadline - time.monotonic()))


def suggest_public_host(metadata):
    """Suggestions never establish reachability or endpoint ownership."""
    for key in ("publicip", "externalip", "hostip"):
        configured = global_ip(metadata.get(key))
        if configured:
            return configured
    return global_ip(routing_ip()) or lookup_ip()
