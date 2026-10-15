"""Bounded public-address suggestions without credentials, proxies or redirects."""

import http.client
import ipaddress
import queue
import socket
import ssl
import threading
import time
import urllib.request

from .transport import NoRedirect

LOOKUP_URL = "https://api.ipify.org"
LOOKUP_TIMEOUT = 5
LOOKUP_BYTES = 64


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


class _LookupBudget:
    """One deadline owns every socket, including connect, handshake and headers."""

    def __init__(self):
        self.deadline = time.monotonic() + LOOKUP_TIMEOUT
        self.lock = threading.Lock()
        self.cancelled = False
        self.connection = None

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if self.cancelled or remaining <= 0:
            raise TimeoutError("Public-address lookup deadline exceeded")
        return remaining

    def track(self, connection):
        with self.lock:
            try:
                self.remaining()
            except TimeoutError:
                connection.close()
                raise
            self.connection = connection
        return connection

    def connect(self, address, timeout=None, source_address=None):
        # System DNS can outlive a socket timeout. The caller remains bounded;
        # once cancelled, this worker cannot open any connection after DNS returns.
        self.remaining()
        choices = socket.getaddrinfo(*address, family=socket.AF_INET, type=socket.SOCK_STREAM)
        failure = OSError("Public-address endpoint is unavailable")
        for family, kind, protocol, _, destination in choices:
            connection = self.track(socket.socket(family, kind, protocol))
            try:
                connection.settimeout(self.remaining())
                if source_address:
                    connection.bind(source_address)
                connection.connect(destination)
                return connection
            except OSError as exc:
                connection.close()
                failure = exc
        raise failure

    def cancel(self):
        with self.lock:
            self.cancelled = True
            connection, self.connection = self.connection, None
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()


class _DeadlineHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, budget, host, **kwargs):
        super().__init__(host, **kwargs)
        self.budget = budget
        self._create_connection = budget.connect

    def connect(self):
        http.client.HTTPConnection.connect(self)
        # Register the TLS socket before handshaking so cancellation also closes
        # an active TLS handshake, rather than only a detached raw socket.
        self.sock = self.budget.track(self._context.wrap_socket(
            self.sock, server_hostname=self.host, do_handshake_on_connect=False))
        self.sock.settimeout(self.budget.remaining())
        self.sock.do_handshake()


class _DeadlineHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, budget):
        super().__init__(context=ssl.create_default_context())
        self.budget = budget

    def https_open(self, req):
        def connection(host, **kwargs):
            return _DeadlineHTTPSConnection(self.budget, host, **kwargs)
        return self.do_open(connection, req, context=self._context, check_hostname=self._check_hostname)


def _lookup_exchange(budget):
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}), NoRedirect(), _DeadlineHTTPSHandler(budget),
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
    budget = _LookupBudget()
    result = queue.Queue(maxsize=1)

    def exchange():
        try:
            result.put(_lookup_exchange(budget))
        except Exception:  # Cancellation may interrupt any urllib/TLS operation.
            result.put(None)

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
