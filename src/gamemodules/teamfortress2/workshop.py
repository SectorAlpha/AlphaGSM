"""Helpers for TF2 workshop desired-state validation."""

import re

from server import ServerError


_WORKSHOP_ID_RE = re.compile(r"^[0-9]+$")


def validate_workshop_id(raw_value: str) -> str:
    """Return a normalized workshop id or raise for invalid input."""

    if not _WORKSHOP_ID_RE.match(str(raw_value)):
        raise ServerError("Workshop entries require a numeric workshop id")
    return str(raw_value)


def raise_experimental_workshop_apply_error():
    """Reject TF2 workshop apply attempts until a verified provider exists."""

    raise ServerError(
        "Workshop support is experimental until a verified TF2 provider is implemented"
    )
