"""Fixed local lifecycle adapter: never remote selectors, command strings or hooks."""

import os
import time
import json
from pathlib import Path
import signal
import subprocess
import sys
from utils.state_io import state_lock, held_descriptor
from .contracts import validate_job, timestamp, utc_now
from .config import local_tag


class RuntimeDeadline(RuntimeError):
    """The bounded local helper timed out; its effects cannot be confirmed."""


class AlphaRuntime:
    """Existing local runtime and Server methods under the existing CLI lock."""

    operation_budget = 540

    @staticmethod
    def helper_command(tag, action):
        command = [sys.executable]
        if not getattr(sys, "frozen", False):
            command.append(str(Path(__file__).resolve().parents[2] / "alphagsm"))
        return command + ["--_agent-runtime", local_tag(tag), action]

    def _operation(self, tag, action, budget):
        # A separate session contains the helper and blocking command children.
        # Existing screen sessions and Docker containers are independently managed.
        # A timeout reports unknown; it never retries the lifecycle operation.
        descriptor = held_descriptor(self.lock_path(tag))
        command = self.helper_command(tag, action)
        if descriptor is not None:
            command += [str(descriptor)]
        with subprocess.Popen(command, pass_fds=() if descriptor is None else (descriptor,), stdout=subprocess.PIPE,
                              stderr=subprocess.DEVNULL, start_new_session=True) as process:
            try:
                output, _ = process.communicate(timeout=budget)
            except subprocess.TimeoutExpired as exc:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)
                raise RuntimeDeadline("Local runtime deadline") from exc
            if process.returncode or len(output) > 1024:
                raise RuntimeError("Local runtime helper failed")
            return json.loads(output)

    @staticmethod
    def lock_path(tag):
        from server.server import DATAPATH

        return os.path.join(DATAPATH, local_tag(tag) + ".json")

    def lock(self, tag):
        return state_lock(self.lock_path(tag))

    def state(self, tag):
        value = self._operation(tag, "status", 20)
        if value not in ("running", "stopped"):
            raise ValueError("Invalid runtime state")
        return value

    @staticmethod
    def metadata(tag, approved):
        from server.server import Server

        server = Server(local_tag(tag))
        selected = dict(approved)
        name = server.data.get("servername")
        capacity = server.data.get("maxplayers")
        if isinstance(name, str):
            selected["name"] = name
        if capacity is not None:
            try:
                selected["capacity"] = int(capacity)
            except (ValueError, TypeError):
                pass
        # Advertised host/port remain an explicit local publication choice.
        # Internal bind addresses and module-local query hooks cannot replace it.
        return selected

    def execute(self, tag, action):
        if action not in ("start", "stop", "restart"):
            raise ValueError("Disallowed lifecycle action")
        self._operation(tag, action, self.operation_budget)


class Executor:
    def __init__(self, config, journal, runtime, authorize, *, lock=None, clock=time.time):
        self.config, self.journal, self.runtime, self.authorize = config, journal, runtime, authorize
        self.lock, self.clock = lock or runtime.lock, clock

    def _result(self, job, outcome, state, category):
        return self.journal.finish(
            {
                "schema_version": 1,
                "job_id": job["job_id"],
                "installation_id": job["installation_id"],
                "outcome": outcome,
                "runtime_state": state,
                "category": category,
                "observed_at": utc_now(),
            }
        )

    def _approved(self, job, cfg):
        binding = cfg["bindings"].get(job["binding_id"])
        if not cfg["management_enabled"] or not cfg["management"] or binding is None:
            return None
        matches = (
            cfg["installation_id"] == job["installation_id"],
            cfg["credential_generation"] == job["credential_generation"],
            cfg["policy_version"] == job["policy_version"],
            binding["epoch"] == job["binding_epoch"],
            job["action"] in binding["actions"],
        )
        if not all(matches):
            return None
        local_tag(binding["tag"])
        return binding

    def run(self, job):
        validate_job(job)
        cfg = self.config.load()
        # Foreign jobs must never contaminate this installation's journal/results.
        if job["installation_id"] != cfg["installation_id"]:
            raise ValueError("Wrong installation")
        record = self.journal.accept(job)
        if record["result"] is not None:
            return record["result"]
        binding = self._approved(job, cfg)
        if record["state"] == "executing":
            state = "unknown"
            if binding:
                try:
                    with self.lock(binding["tag"]):
                        state = self.runtime.state(binding["tag"])
                except (OSError, ValueError, RuntimeError):
                    pass
            return self._result(job, "unknown", state, "interrupted")
        if binding is None:
            return self._result(job, "failed", "unknown", "denied")
        if timestamp(job["issued_at"]) > self.clock() + 30 or timestamp(job["expires_at"]) <= self.clock():
            return self._result(job, "failed", "unknown", "expired")
        try:
            # Server lock precedes state loading. The config lock serializes local
            # policy changes with the final authorization and lifecycle operation.
            with self.lock(binding["tag"]), state_lock(self.config.path):
                cfg = self.config.load()
                binding = self._approved(job, cfg)
                if binding is None or timestamp(job["expires_at"]) <= self.clock():
                    return self._result(job, "failed", "unknown", "denied")
                try:
                    allowed = self.authorize(job)
                except (OSError, ValueError):
                    allowed = False
                if allowed is not True:
                    return self._result(job, "failed", "unknown", "denied")
                self.journal.executing(job["job_id"])
                state = self.runtime.state(binding["tag"])
                action = job["action"]
                if action == "restart" and state != "running":
                    return self._result(job, "failed", state, "precondition")
                if action != "status" and not (
                    (action == "start" and state == "running") or (action == "stop" and state == "stopped")
                ):
                    self.runtime.execute(binding["tag"], action)
                    state = self.runtime.state(binding["tag"])
                expected = "stopped" if action == "stop" else "running"
                if action != "status" and state != expected:
                    return self._result(job, "failed", state, "execution_failed")
                return self._result(job, "succeeded", state, "ok")
        except RuntimeDeadline:
            return self._result(job, "unknown", "unknown", "budget_exceeded")
        except Exception:  # trusted runtime may raise module-specific exceptions
            return self._result(
                job,
                "unknown" if self.journal.get(job["job_id"])["state"] == "executing" else "failed",
                "unknown",
                "execution_failed",
            )
