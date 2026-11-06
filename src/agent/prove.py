# pylint: disable=unidiomatic-typecheck
"""Place a website ownership token in the live TeamSpeak name, then restore it."""

import json
import os
import re
import time

TOKEN = re.compile(r"SA-[A-Za-z0-9_-]{43}\Z")
NAME_LIMIT = 64


class QueryBusy(Exception):
    """Sector Alpha is still finishing another query for this server."""


def temporary_name(current, token):
    """Keep the current name when the token still fits; otherwise show only the token."""
    if type(current) is not str:
        raise ValueError("TeamSpeak did not return a server name")
    combined = (current + " " + token).strip()
    if len(combined.encode()) <= NAME_LIMIT:
        return combined
    if len(token.encode()) <= NAME_LIMIT:
        return token
    raise ValueError("Ownership challenge does not fit in the TeamSpeak server name")


def prove_name(
    tag, token, *, pending_path, read_name, write_name, request, poll, sleep=time.sleep, attempts=20, request_attempts=8
):
    """Swap the live name for one check. The previous name is restored on every exit."""
    if type(tag) is not str or not tag:
        raise ValueError("Choose one local TeamSpeak server")
    if not TOKEN.fullmatch(token or ""):
        raise ValueError("Ownership challenge is not a current SA- token")
    _recover(pending_path, tag, write_name)
    current = read_name()
    updated = temporary_name(current, token)
    _write_pending(pending_path, tag, current)
    write_name(updated)
    try:
        job = _request_when_idle(request, sleep, request_attempts)
        state = {"state": "queued", "verified": False}
        for _ in range(attempts):
            state = poll(job["job_id"])
            if state.get("state") not in ("queued", "claimed"):
                return state
            sleep(3)
        return state
    finally:
        write_name(current)
        if pending_path.exists():
            pending_path.unlink()


def _request_when_idle(request, sleep, attempts):
    error = QueryBusy("Sector Alpha is still querying this server")
    for attempt in range(attempts):
        try:
            return request()
        except QueryBusy as exc:
            error = exc
            if attempt + 1 == attempts:
                break
            sleep(2)
    raise error


def _recover(path, tag, write_name):
    if not path.exists():
        return
    saved = json.loads(path.read_text(encoding="utf-8"))
    if saved.get("tag") != tag or type(saved.get("name")) is not str:
        raise ValueError("Finish the interrupted name proof for " + str(saved.get("tag") or "the other server"))
    write_name(saved["name"])
    path.unlink()


def _write_pending(path, tag, name):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump({"tag": tag, "name": name}, handle)
    os.chmod(path, 0o600)
