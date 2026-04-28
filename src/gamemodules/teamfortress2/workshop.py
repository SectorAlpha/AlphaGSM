"""Helpers for TF2 workshop desired-state validation."""

import re

from server import ServerError


_WORKSHOP_ID_RE = re.compile(r"^[0-9]+$")


def validate_workshop_id(raw_value: str) -> str:
    """Return a normalized workshop id or raise for invalid input."""

    if not _WORKSHOP_ID_RE.match(str(raw_value)):
        raise ServerError("Workshop entries require a numeric workshop id")
    return str(raw_value)
