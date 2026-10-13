"""Durable processed IDs: persist intent and result before network acknowledgement."""

import json
import time
from pathlib import Path
from utils.state_io import atomic_write_text, state_lock
from .contracts import validate_job, validate_result


class Journal:
    def __init__(self, path):
        self.path = Path(path)

    def _load(self):
        if not self.path.exists():
            return {}
        if self.path.is_symlink() or self.path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError("Unsafe agent journal")
        return json.loads(self.path.read_text())

    def _write(self, value):
        # Retain processed IDs for 30 days; never expire executing/accepted intents.
        now = time.time()
        value = {
            k: v for k, v in value.items() if v["state"] in ("accepted", "executing") or v["at"] > now - 30 * 86400
        }
        if len(value) > 10000:
            raise ValueError("Journal capacity exhausted; no new actions may begin")
        atomic_write_text(self.path, json.dumps(value, sort_keys=True), mode=0o600)

    def get(self, job_id):
        with state_lock(self.path):
            return self._load().get(job_id)

    def accept(self, job):
        validate_job(job)
        with state_lock(self.path):
            value = self._load()
            previous = value.get(job["job_id"])
            if previous is not None:
                if previous["job"] != job:
                    raise ValueError("Job identity reused with different contract")
                return previous
            record = {"job": job, "state": "accepted", "result": None, "at": time.time(), "acknowledged": False}
            value[job["job_id"]] = record
            self._write(value)
            return record

    def executing(self, job_id):
        with state_lock(self.path):
            value = self._load()
            if value[job_id]["state"] != "accepted":
                raise ValueError("Invalid local execution transition")
            value[job_id]["state"] = "executing"
            self._write(value)

    def finish(self, result):
        validate_result(result)
        with state_lock(self.path):
            value = self._load()
            value[result["job_id"]].update(state="result", result=result, at=time.time())
            self._write(value)
        return result

    def pending_results(self):
        with state_lock(self.path):
            return [r["result"] for r in self._load().values() if r["state"] == "result" and not r["acknowledged"]]

    def acknowledge(self, job_id):
        with state_lock(self.path):
            value = self._load()
            value[job_id]["acknowledged"] = True
            self._write(value)
