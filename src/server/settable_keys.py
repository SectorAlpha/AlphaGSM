from __future__ import annotations

from dataclasses import dataclass


class KeyResolutionError(ValueError):
    """Raised when a user-facing setting key cannot be resolved."""


@dataclass(frozen=True)
# pylint: disable=too-many-instance-attributes
class SettingSpec:
    canonical_key: str
    aliases: tuple[str, ...] = ()
    description: str = ""
    value_type: str = "string"
    apply_to: tuple[str, ...] = ("datastore",)
    storage_key: str | None = None
    native_config_key: str | None = None
    native_config_path: tuple[str, ...] | None = None
    launch_arg_tokens: tuple[str, ...] | None = None
    launch_arg_format: str | None = None
    secret: bool = False
    examples: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResolvedSetting:
    canonical_key: str
    input_key: str
    storage_key: str
    spec: SettingSpec


COMMON_SETTING_ALIASES = {
    "adminpassword": ("adminpass", "admin_password"),
    "bindaddress": ("bind_address",),
    "contactemail": ("email", "contact_email"),
    "hostname": ("servername", "server_name", "name"),
    "map": ("gamemap", "startmap", "level", "worldname"),
    "maxplayers": ("max_players", "users"),
    "port": ("gameport",),
    "queryport": ("query_port",),
    "rconpassword": (
        "rconpass",
        "rcon_password",
        "querypassword",
        "query_administrator_password",
    ),
    "servername": ("hostname", "server_name", "name"),
    "serverpassword": ("sv_password", "svpassword", "password"),
    "startmap": ("map", "gamemap", "level", "world"),
    "worldname": ("world", "world_name", "map", "gamemap", "levelname"),
}


def normalize_setting_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def get_effective_aliases(spec: SettingSpec, schema: dict[str, SettingSpec] | None = None):
    """Return schema aliases plus collision-safe common aliases for *spec*."""

    aliases = []
    seen = {normalize_setting_name(spec.canonical_key)}
    for alias in spec.aliases:
        normalized = normalize_setting_name(alias)
        if normalized in seen:
            continue
        seen.add(normalized)
        aliases.append(alias)

    for alias in COMMON_SETTING_ALIASES.get(spec.canonical_key, ()):
        normalized = normalize_setting_name(alias)
        if normalized in seen:
            continue
        if schema is not None and _is_name_claimed_by_other_spec(normalized, spec, schema):
            continue
        seen.add(normalized)
        aliases.append(alias)

    return tuple(aliases)


def _is_name_claimed_by_other_spec(
    normalized_name: str,
    current_spec: SettingSpec,
    schema: dict[str, SettingSpec],
):
    """Return true when another schema entry already claims *normalized_name*."""

    for other_spec in schema.values():
        if other_spec is current_spec:
            continue
        other_names = {normalize_setting_name(other_spec.canonical_key)}
        other_names.update(normalize_setting_name(alias) for alias in other_spec.aliases)
        other_names.update(
            normalize_setting_name(alias)
            for alias in COMMON_SETTING_ALIASES.get(other_spec.canonical_key, ())
        )
        if normalized_name in other_names:
            return True
    return False


def redact_value(spec: SettingSpec, value):
    return "<redacted>" if spec.secret and value not in (None, "", [], {}, ()) else value


def resolve_requested_key(raw_key: str, schema: dict[str, SettingSpec]) -> ResolvedSetting:
    normalized = normalize_setting_name(raw_key)
    matched_specs: list[SettingSpec] = []
    for _, spec in schema.items():
        names = {normalize_setting_name(spec.canonical_key)}
        names.update(normalize_setting_name(alias) for alias in get_effective_aliases(spec, schema))
        if normalized in names:
            matched_specs.append(spec)

    if not matched_specs:
        raise KeyResolutionError(f"Unsupported setting key: {raw_key}")

    unique_specs = set(matched_specs)
    if len(unique_specs) > 1:
        raise KeyResolutionError(f"Ambiguous setting key: {raw_key}")

    spec = matched_specs[0]
    return ResolvedSetting(
        canonical_key=spec.canonical_key,
        input_key=raw_key,
        storage_key=spec.storage_key or spec.canonical_key,
        spec=spec,
    )


def build_native_config_values(
    data,
    schema: dict[str, SettingSpec],
    *,
    defaults=None,
    key_overrides=None,
    value_transform=None,
    require_explicit_key=False,
):
    """Build a native-config mapping from schema-backed datastore values."""

    defaults = defaults or {}
    key_overrides = key_overrides or {}
    values = {}
    seen = set()

    for spec in schema.values():
        signature = (
            spec.canonical_key,
            spec.storage_key or spec.canonical_key,
            spec.native_config_key,
        )
        if signature in seen or "native_config" not in spec.apply_to:
            continue
        seen.add(signature)

        storage_key = spec.storage_key or spec.canonical_key
        if storage_key in data:
            value = data[storage_key]
        elif storage_key in defaults:
            value = defaults[storage_key]
        else:
            continue

        config_key = key_overrides.get(spec.canonical_key)
        if config_key is None:
            config_key = spec.native_config_key
        if config_key is None:
            if require_explicit_key:
                continue
            config_key = storage_key

        if value_transform is not None:
            value = value_transform(spec, value)
        values[config_key] = value

    return values


def build_native_config_tree(
    data,
    schema: dict[str, SettingSpec],
    *,
    defaults=None,
    path_overrides=None,
    value_transform=None,
    require_explicit_path=False,
):
    """Build a nested native-config tree from schema-backed datastore values."""

    defaults = defaults or {}
    path_overrides = path_overrides or {}
    values = {}
    seen = set()

    for spec in schema.values():
        signature = (
            spec.canonical_key,
            spec.storage_key or spec.canonical_key,
            spec.native_config_path,
            spec.native_config_key,
        )
        if signature in seen or "native_config" not in spec.apply_to:
            continue
        seen.add(signature)

        storage_key = spec.storage_key or spec.canonical_key
        if storage_key in data:
            value = data[storage_key]
        elif storage_key in defaults:
            value = defaults[storage_key]
        else:
            continue

        path = path_overrides.get(spec.canonical_key)
        if path is None:
            path = spec.native_config_path
        if path is None and spec.native_config_key is not None:
            path = (spec.native_config_key,)
        if path is None:
            if require_explicit_path:
                continue
            path = (storage_key,)

        if value_transform is not None:
            value = value_transform(spec, value)

        target = values
        for segment in path[:-1]:
            target = target.setdefault(segment, {})
        target[path[-1]] = value

    return values


def merge_nested_config(base, updates):
    """Recursively merge nested config updates into *base*."""

    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge_nested_config(base[key], value)
        elif isinstance(value, dict):
            base[key] = dict(value)
        else:
            base[key] = value
    return base


def build_launch_arg_values(
    data,
    schema: dict[str, SettingSpec],
    *,
    defaults=None,
    token_overrides=None,
    value_transform=None,
    require_explicit_tokens=False,
):
    """Build ordered launch-argument tokens from schema-backed datastore values."""

    defaults = defaults or {}
    token_overrides = token_overrides or {}
    tokens = []
    seen = set()

    for spec in schema.values():
        signature = (
            spec.canonical_key,
            spec.storage_key or spec.canonical_key,
            spec.launch_arg_tokens,
            spec.launch_arg_format,
        )
        if signature in seen or "launch_args" not in spec.apply_to:
            continue
        seen.add(signature)

        storage_key = spec.storage_key or spec.canonical_key
        if storage_key in data:
            value = data[storage_key]
        elif storage_key in defaults:
            value = defaults[storage_key]
        else:
            continue

        arg_tokens = token_overrides.get(spec.canonical_key)
        if arg_tokens is None:
            arg_tokens = spec.launch_arg_tokens
        if arg_tokens is None and spec.launch_arg_format is None:
            if require_explicit_tokens:
                continue
            arg_tokens = (storage_key,)

        if value_transform is not None:
            value = value_transform(spec, value)
        if arg_tokens is not None:
            tokens.extend(arg_tokens)
            if value is not None:
                tokens.append(value)
        elif spec.launch_arg_format is not None:
            tokens.append(spec.launch_arg_format.format(value=value))

    return tokens
