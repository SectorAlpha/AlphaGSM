"""Explicit optional outbound service; reporting survives management outages."""

import secrets
import threading
import time
from utils.state_io import state_lock
from .journal import Journal
from .lifecycle import AlphaRuntime, Executor
from .reporting import policy_snapshot, report_snapshot
from .preflight import final_report, preflight_report
from .socket_channel import SocketChannel, SocketError
from .transport import AgentLimit, Transport, TransportError


class Service:  # pylint: disable=too-many-instance-attributes
    def __init__(self, config, *, runtime=None, transport=None, channel_factory=None):
        self.config = config
        self.runtime = runtime or AlphaRuntime()
        cfg = config.load()
        self.relationship = (cfg["origin"], cfg["installation_id"])
        self.transport = transport or Transport(cfg["origin"])
        self.journal = Journal(config.root / "journal.json")
        self.session_id = secrets.token_hex(16)
        self.stop = threading.Event()
        if channel_factory is not None:
            self.channel_factory = channel_factory

    def report_once(self):
        cfg = self.config.load()
        if not cfg["reporting"] or (cfg["origin"], cfg["installation_id"]) != self.relationship:
            return None
        payload = report_snapshot(self.config, self.runtime)
        checked = self.config.load()
        payload, failures = preflight_report(payload, checked)
        # DNS is outside the policy lock. The final approval check and send are
        # serialized with local consent, endpoint and credential mutations.
        with state_lock(self.config.path):
            current = self.config.load()
            if (not current['reporting'] or (current['origin'], current['installation_id']) != self.relationship
                    or current['origin'] != checked['origin']
                    or current['installation_id'] != payload['installation_id']):
                return None
            payload, changed = final_report(payload, checked, current)
            failures.update(changed)
            for binding_id, reason in failures.items():
                print("Publication withheld for " + binding_id + ": " + reason)
            return self.transport.request("POST", "/v1/agent/reports", credential=current["reporting"], payload=payload)

    def management_once(self, *, wait=25):
        cfg = self.config.load()
        if not cfg["management_enabled"] or (cfg["origin"], cfg["installation_id"]) != self.relationship:
            return None
        credential = cfg["management"]
        self.transport.request("POST", "/v1/agent/policy", credential=credential, payload=policy_snapshot(cfg))
        options = {"timeout": 35}
        if wait == 0:
            # A live socket must not also hold the 25-second poll.
            options = {"timeout": 10, "query": "wait=0"}
        response = self.transport.request(
            "GET", "/v1/agent/jobs", credential=credential, session_id=self.session_id, **options
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
            if (not latest["management_enabled"]
                    or (latest["origin"], latest["installation_id"]) != self.relationship):
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

    def _open_channel(self, cfg):
        factory = getattr(self, "channel_factory", None)
        if factory is not None:
            return factory(cfg, self.session_id)
        return SocketChannel(cfg["origin"], cfg["reporting"], self.session_id)

    def _connection_once(self):
        cfg = self.config.load()
        if (cfg["origin"], cfg["installation_id"]) != self.relationship:
            return "idle"
        if not cfg["reporting"]:
            if cfg["management_enabled"]:
                self.management_once()
                return "rest"
            return "idle"
        try:
            opened = self._open_channel(cfg)
        except AgentLimit:
            raise
        except (OSError, TransportError, ValueError):
            if cfg["management_enabled"]:
                self.management_once()
                return "fallback"
            return "retry"
        with opened as channel:
            self._serve_channel(channel)
        return "socket"

    def _serve_channel(self, channel):
        worker = None
        interval = getattr(self, "heartbeat_interval", 30)
        next_beat = time.monotonic() + interval
        try:
            while not self.stop.is_set():
                if worker is not None and not worker.is_alive():
                    worker = None
                timeout = max(0.05, min(interval, next_beat - time.monotonic()))
                frame = channel.recv(timeout)
                # The frame only names a job. Fetching, local checks, authorize, and the result post stay on HTTPS.
                if isinstance(frame, dict) and frame.get("type") == "request" and worker is None:
                    worker = threading.Thread(target=self._run_requested_job, name="alphagsm-agent-job", daemon=True)
                    worker.start()
                elif isinstance(frame, dict) and frame.get("type") == "heartbeat":
                    next_beat = time.monotonic() + interval
                if time.monotonic() >= next_beat and not self.stop.is_set():
                    channel.send({"type": "heartbeat"})
                    next_beat = time.monotonic() + interval
        finally:
            if worker is not None:
                worker.join()

    def _run_requested_job(self):
        try:
            self.management_once(wait=0)
        except (TransportError, ValueError, OSError):
            pass

    def _management_loop(self):
        failures = 0
        while not self.stop.is_set():
            try:
                outcome = self._connection_once()
            except AgentLimit:
                failures = min(failures + 1, 6)
                self.stop.wait(max(60, min(300, 2 ** failures)) + secrets.randbelow(5))
                continue
            except (SocketError, TransportError, ValueError, OSError):
                failures = min(failures + 1, 6)
                self.stop.wait(min(300, 2 ** failures) + secrets.randbelow(5))
                continue
            if outcome == "socket":
                failures = 0
                self.stop.wait(1)
                continue
            if outcome in ("rest", "fallback"):
                failures = 0
                continue
            failures = min(failures + 1, 6)
            self.stop.wait(5 if outcome == "idle" else min(300, 2 ** failures) + secrets.randbelow(5))

    def run(self):
        with state_lock(self.config.root / "service", timeout=0):
            reporter = threading.Thread(target=self._report_loop, daemon=True)
            reporter.start()
            try:
                self._management_loop()
            finally:
                self.stop.set()
                reporter.join(timeout=40)
