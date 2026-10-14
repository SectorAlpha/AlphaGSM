"""Explicit optional outbound service; reporting survives management outages."""

import secrets
import threading
import time
from utils.state_io import state_lock
from .journal import Journal
from .lifecycle import AlphaRuntime, Executor
from .reporting import policy_snapshot, report_snapshot
from .transport import Transport, TransportError


class Service:
    def __init__(self, config, *, runtime=None, transport=None):
        self.config = config
        self.runtime = runtime or AlphaRuntime()
        cfg = config.load()
        self.transport = transport or Transport(cfg["origin"])
        self.journal = Journal(config.root / "journal.json")
        self.session_id = secrets.token_hex(16)
        self.stop = threading.Event()

    def report_once(self):
        cfg = self.config.load()
        if not cfg["reporting"]:
            return None
        payload = report_snapshot(self.config, self.runtime)
        return self.transport.request("POST", "/v1/agent/reports", credential=cfg["reporting"], payload=payload)

    def management_once(self):
        cfg = self.config.load()
        if not cfg["management_enabled"]:
            return None
        credential = cfg["management"]
        self.transport.request("POST", "/v1/agent/policy", credential=credential, payload=policy_snapshot(cfg))
        response = self.transport.request(
            "GET", "/v1/agent/jobs", credential=credential, session_id=self.session_id, timeout=35
        )
        # Poll establishes a session before sending any previously unacknowledged result.
        for result in self.journal.pending_results():
            if result["installation_id"] != cfg["installation_id"]:
                continue
            self.transport.request(
                "POST", "/v1/agent/results", credential=credential, payload=result, session_id=self.session_id
            )
            self.journal.acknowledge(result["job_id"])
        job = response.get("job")
        if job is None:
            return None

        def authorize(value):
            latest = self.config.load()
            if not latest["management_enabled"]:
                return False
            result = self.transport.request(
                "POST",
                "/v1/agent/jobs/" + value["job_id"] + "/authorize",
                credential=latest["management"],
                session_id=self.session_id,
            )
            return result.get("authorized") is True

        result = Executor(self.config, self.journal, self.runtime, authorize).run(job)
        self.transport.request(
            "POST", "/v1/agent/results", credential=credential, payload=result, session_id=self.session_id
        )
        self.journal.acknowledge(job["job_id"])
        return result

    def _report_loop(self):
        next_report = 0
        last_dirty = 0
        failures = 0
        while not self.stop.wait(1):
            cfg = self.config.load()
            dirty = cfg["dirty_at"]
            if cfg["reporting_enabled"] and (
                time.monotonic() >= next_report or (failures == 0 and dirty != last_dirty and time.time() >= dirty + 5)
            ):
                try:
                    self.report_once()
                    failures = 0
                    last_dirty = dirty
                    next_report = time.monotonic() + 55 + secrets.randbelow(11)
                except (TransportError, ValueError, TimeoutError):
                    failures = min(failures + 1, 6)
                    next_report = time.monotonic() + min(300, 2**failures) + secrets.randbelow(5)
                    # Lifecycle operations can hold the config lock longer than
                    # reporting's lock budget. Retry without ending the reporter.
                    # An outage never changes the result of a successful local CLI command.

    def _management_loop(self):
        failures = 0
        while not self.stop.is_set():
            cfg = self.config.load()
            if not cfg["management_enabled"]:
                self.stop.wait(1)
                continue
            try:
                self.management_once()
                failures = 0
            except (TransportError, ValueError):
                failures = min(failures + 1, 6)
                self.stop.wait(min(300, 2**failures) + secrets.randbelow(5))

    def run(self):
        with state_lock(self.config.root / "service", timeout=0):
            reporter = threading.Thread(target=self._report_loop, daemon=True)
            reporter.start()
            try:
                self._management_loop()
            finally:
                self.stop.set()
                reporter.join(timeout=40)
