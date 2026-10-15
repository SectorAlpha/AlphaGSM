# pylint: disable=unidiomatic-typecheck
"""Dependency-free version-one contracts shared with compatible control services."""

from datetime import datetime, timezone
import re

ACTIONS = frozenset(("status", "start", "stop", "restart"))
STATES = frozenset(("running", "stopped", "unknown"))
OUTCOMES = frozenset(("succeeded", "failed", "unknown"))
CATEGORIES = frozenset(
    ("ok", "precondition", "denied", "expired", "execution_failed", "interrupted", "budget_exceeded")
)
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


class ContractError(ValueError):
    """Untrusted JSON does not satisfy the closed protocol."""


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ContractError("Unexpected or missing fields")
    return value


def identifier(value):
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        raise ContractError("Invalid identifier")
    return value


def integer(value, minimum=1, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError("Invalid integer")
    return value


def text(value, maximum=256):
    if type(value) is not str or len(value.encode("utf-8")) > maximum or any(ord(c) < 32 for c in value):
        raise ContractError("Invalid bounded text")
    return value


def enum(value, choices):
    if type(value) is not str or value not in choices:
        raise ContractError("Invalid enum")
    return value


def timestamp(value):
    if type(value) is not str or len(value) > 40:
        raise ContractError("Invalid timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractError("Invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ContractError("Timestamp must be UTC")
    return parsed.timestamp()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def validate_job(value):
    exact(
        value,
        (
            "schema_version",
            "job_id",
            "installation_id",
            "binding_id",
            "binding_epoch",
            "action",
            "policy_version",
            "credential_generation",
            "requested_by",
            "issued_at",
            "expires_at",
        ),
    )
    integer(value["schema_version"], 1, 1)
    for key in ("job_id", "installation_id", "binding_id", "requested_by"):
        identifier(value[key])
    for key in ("binding_epoch", "policy_version", "credential_generation"):
        integer(value[key])
    enum(value["action"], ACTIONS)
    issued, expires = timestamp(value["issued_at"]), timestamp(value["expires_at"])
    if not 0 < expires - issued <= 120:
        raise ContractError("Invalid job lifetime")
    return value


def validate_metadata(value):
    optional = ("connect_port",) if type(value) is dict and "connect_port" in value else ()
    exact(
        value,
        (
            "binding_id",
            "binding_epoch",
            "publication",
            "name",
            "game_id",
            "host",
            "port",
            "capacity",
            "runtime_state",
            "allowed_actions",
        ) + optional,
    )
    identifier(value["binding_id"])
    integer(value["binding_epoch"])
    if type(value["publication"]) is not bool:
        raise ContractError("Publication must be boolean")
    for key in ("name", "game_id", "host"):
        text(value[key])
    integer(value["port"], 1, 65535)
    if value.get("connect_port") is not None:
        integer(value["connect_port"], 1, 65535)
    integer(value["capacity"], 0, 100000)
    enum(value["runtime_state"], STATES)
    actions = value["allowed_actions"]
    if type(actions) is not list or len(actions) > 4 or len(set(map(str, actions))) != len(actions):
        raise ContractError("Invalid actions")
    for action in actions:
        enum(action, ACTIONS)
    return value


def validate_report(value):
    exact(value, ("schema_version", "installation_id", "sequence", "policy_version", "bindings"))
    integer(value["schema_version"], 1, 1)
    identifier(value["installation_id"])
    integer(value["sequence"])
    integer(value["policy_version"])
    bindings = value["bindings"]
    if type(bindings) is not list or len(bindings) > 100:
        raise ContractError("Invalid binding collection")
    for binding in bindings:
        validate_metadata(binding)
    if len({b["binding_id"] for b in bindings}) != len(bindings):
        raise ContractError("Duplicate binding")
    return value


def validate_result(value):
    exact(value, ("schema_version", "job_id", "installation_id", "outcome", "runtime_state", "category", "observed_at"))
    integer(value["schema_version"], 1, 1)
    identifier(value["job_id"])
    identifier(value["installation_id"])
    enum(value["outcome"], OUTCOMES)
    enum(value["runtime_state"], STATES)
    enum(value["category"], CATEGORIES)
    timestamp(value["observed_at"])
    return value


def validate_policy(value):
    exact(value, ("schema_version", "installation_id", "policy_version", "bindings"))
    integer(value["schema_version"], 1, 1)
    identifier(value["installation_id"])
    integer(value["policy_version"])
    if type(value["bindings"]) is not list or len(value["bindings"]) > 100:
        raise ContractError("Invalid binding collection")
    seen = set()
    for item in value["bindings"]:
        exact(item, ("binding_id", "binding_epoch", "allowed_actions"))
        identifier(item["binding_id"])
        integer(item["binding_epoch"])
        if item["binding_id"] in seen:
            raise ContractError("Duplicate binding")
        seen.add(item["binding_id"])
        if type(item["allowed_actions"]) is not list or len(item["allowed_actions"]) > 4:
            raise ContractError("Invalid actions")
        for action in item["allowed_actions"]:
            enum(action, ACTIONS)
    return value
