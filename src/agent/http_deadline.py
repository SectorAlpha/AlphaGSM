"""Reusable total HTTPS deadlines with active socket cancellation and no late connect."""

import http.client
import queue
import socket
import ssl
import threading
import time
import urllib.request


class DeadlineBudget:
    """One deadline owns every socket, including connect, handshake and headers."""

    def __init__(self, timeout, *, family=socket.AF_UNSPEC):
        self.deadline = time.monotonic() + timeout
        self.family = family
        self.lock = threading.Lock()
        self.cancelled = False
        self.connection = None

    def remaining(self):
        remaining = self.deadline - time.monotonic()
        if self.cancelled or remaining <= 0:
            raise TimeoutError("HTTPS total deadline exceeded")
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
        choices = socket.getaddrinfo(*address, family=self.family, type=socket.SOCK_STREAM)
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


class DeadlineHTTPSConnection(http.client.HTTPSConnection):
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


class DeadlineHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, budget=None, *, context=None):
        super().__init__(context=context or ssl.create_default_context())
        self.budget = budget

    def https_open(self, req):
        budget = self.budget or getattr(req, "agent_deadline", None)
        if budget is None:
            return super().https_open(req)
        def connection(host, **kwargs):
            return DeadlineHTTPSConnection(budget, host, **kwargs)
        return self.do_open(connection, req, context=self._context)


def bounded_exchange(operation, budget, *, name):
    result = queue.Queue(maxsize=1)

    def exchange():
        try:
            result.put((True, operation()))
        except Exception as exc:
            result.put((False, exc))

    worker = threading.Thread(target=exchange, daemon=True, name=name)
    worker.start()
    try:
        accepted, value = result.get(timeout=budget.remaining())
        if not accepted:
            raise value
        return value
    except queue.Empty:
        raise TimeoutError("HTTPS total deadline exceeded") from None
    finally:
        budget.cancel()
        worker.join(timeout=max(0, budget.deadline - time.monotonic()))
