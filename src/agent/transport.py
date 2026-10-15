# pylint: disable=unidiomatic-typecheck
"""Fixed-origin verified HTTPS without proxies, redirects or unbounded responses."""

import http.client
import json
import ssl
import time
import threading
import urllib.error
import urllib.request
from .config import canonical_agent_origin
from .http_deadline import DeadlineBudget, DeadlineHTTPSHandler, bounded_exchange

REPORT_TIMEOUT = 10


class TransportError(OSError):
    """Bounded category-only network failures; credentials are never in errors."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TransportError("Credential redirects are forbidden")


class Transport:
    def __init__(self, api_origin, *, context=None):
        self.origin = canonical_agent_origin(api_origin)
        self.report_lock = threading.Lock()
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            NoRedirect(),
            DeadlineHTTPSHandler(context=context or ssl.create_default_context()),
        )

    def request(self, method, path, *, credential=None, payload=None, session_id=None, timeout=10):
        if path not in (
            "/v1/agent/enroll",
            "/v1/agent/bindings",
            "/v1/agent/reports",
            "/v1/agent/policy",
            "/v1/agent/jobs",
            "/v1/agent/results",
        ) and not (
            path.startswith("/v1/agent/jobs/")
            and path.endswith("/authorize")
            and path.count("/") == 5
            and all(c.isalnum() or c in "/_-" for c in path)
        ):
            raise ValueError("Unapproved agent route")
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode()
            if len(data) > 131072:
                raise TransportError("Request exceeds byte limit")
            headers["Content-Type"] = "application/json"
        if credential is not None:
            headers["Authorization"] = "Bearer " + credential["key_id"] + "." + credential["secret"]
        if session_id is not None:
            headers["X-Agent-Session"] = session_id
        request = urllib.request.Request(self.origin + path, method=method, data=data, headers=headers)
        try:
            if method == "POST" and path == "/v1/agent/reports":
                return self._report_request(request, min(timeout, REPORT_TIMEOUT))
            return self._read_response(request, timeout)
        except urllib.error.HTTPError as exc:
            raise TransportError("HTTPS request rejected (%s)" % exc.code) from None
        except (OSError, ValueError, http.client.HTTPException, RecursionError) as exc:
            if isinstance(exc, TransportError):
                raise
            raise TransportError("HTTPS exchange failed") from None


    def _report_request(self, request, timeout):
        if not self.report_lock.acquire(blocking=False):
            raise TransportError("A timed-out report is still awaiting DNS cleanup")
        budget = DeadlineBudget(timeout)
        request.agent_deadline = budget

        def send():
            try:
                return self._read_response(request, budget.remaining())
            finally:
                self.report_lock.release()

        return bounded_exchange(send, budget, name="alphagsm-report-post")

    def _read_response(self, request, timeout):
        deadline = time.monotonic() + timeout
        with self.opener.open(request, timeout=timeout) as response:
            if response.geturl() != request.full_url:
                raise TransportError("Response origin changed")
            parts = bytearray()
            while response.fp is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TransportError("HTTPS total deadline exceeded")
                # urllib's TLS socket must share the total deadline across reads.
                response.fp.raw._sock.settimeout(remaining)  # pylint: disable=protected-access
                chunk = response.read1(min(16384, 131073 - len(parts)))
                parts.extend(chunk)
                if len(parts) > 131072:
                    raise TransportError("Response exceeds byte limit")
                if not chunk:
                    break
            result = json.loads(parts)
            if type(result) is not dict:
                raise TransportError("Invalid HTTPS response")
            return result
