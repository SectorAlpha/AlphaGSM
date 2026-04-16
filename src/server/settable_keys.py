from __future__ import annotations

from dataclasses import dataclass


class KeyResolutionError(ValueError):
    """Raised when a user-facing setting key cannot be resolved."""


@dataclass(frozen=True)
class SettingSpec:
    canonical_key: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    value_type: str = "string"
    apply_to: tuple[str, ...] = ("datastore",)
    storage_key: str | None = None
    secret: bool = False
    examples: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedSetting:
    canonical_key: str
    input_key: str
    storage_key: str
    spec: SettingSpec


def normalize_setting_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def redact_value(spec: SettingSpec, value):
    return "<redacted>" if spec.secret and value not in (None, "") else value


def resolve_requested_key(raw_key: str, schema: dict[str, SettingSpec]) -> ResolvedSetting:
    normalized = normalize_setting_name(raw_key)
    for canonical_key, spec in schema.items():
        names = {normalize_setting_name(canonical_key)}
        names.update(normalize_setting_name(alias) for alias in spec.aliases)
        if normalized in names:
            return ResolvedSetting(
                canonical_key=canonical_key,
                input_key=raw_key,
                storage_key=spec.storage_key or canonical_key,
                spec=spec,
            )
    raise KeyResolutionError(f"Unsupported setting key: {raw_key}")
