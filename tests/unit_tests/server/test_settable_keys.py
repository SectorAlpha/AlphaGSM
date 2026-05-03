from server.settable_keys import (
    KeyResolutionError,
    SettingSpec,
    build_native_config_tree,
    build_native_config_values,
    build_launch_arg_values,
    merge_nested_config,
    normalize_setting_name,
    redact_value,
    resolve_requested_key,
)

import pytest


def test_normalize_setting_name_collapses_case_and_separators():
    assert normalize_setting_name("Game-Map") == "gamemap"
    assert normalize_setting_name("server_name") == "servername"


def test_resolve_requested_key_uses_schema_aliases():
    schema = {
        "start-map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "startmap", "level"),
            description="Current map",
            value_type="string",
            apply_to=("datastore", "launch_args"),
        )
    }

    resolved = resolve_requested_key("game-map", schema)

    assert resolved.canonical_key == "map"
    assert resolved.storage_key == "map"
    assert resolved.input_key == "game-map"


def test_resolve_requested_key_uses_common_aliases_without_schema_repetition():
    schema = {
        "server_name": SettingSpec(
            canonical_key="servername",
            description="Current public name",
            value_type="string",
        )
    }

    resolved = resolve_requested_key("hostname", schema)

    assert resolved.canonical_key == "servername"
    assert resolved.storage_key == "servername"


def test_resolve_requested_key_skips_common_alias_that_conflicts_with_other_key():
    schema = {
        "map": SettingSpec(
            canonical_key="map",
            description="Current map",
            value_type="string",
        ),
        "startmap": SettingSpec(
            canonical_key="startmap",
            description="Startup map",
            value_type="string",
        ),
    }

    resolved = resolve_requested_key("startmap", schema)

    assert resolved.canonical_key == "startmap"


def test_resolve_requested_key_skips_worldname_common_alias_when_map_exists():
    schema = {
        "map": SettingSpec(
            canonical_key="map",
            description="Current map",
            value_type="string",
        ),
        "worldname": SettingSpec(
            canonical_key="worldname",
            description="Current world",
            value_type="string",
        ),
    }

    resolved = resolve_requested_key("map", schema)

    assert resolved.canonical_key == "map"


def test_resolve_requested_key_uses_common_rcon_aliases_without_schema_repetition():
    schema = {
        "rconpassword": SettingSpec(
            canonical_key="rconpassword",
            description="RCON password",
            value_type="string",
        )
    }

    resolved = resolve_requested_key("querypassword", schema)

    assert resolved.canonical_key == "rconpassword"


def test_resolve_requested_key_rejects_unknown_input():
    with pytest.raises(KeyResolutionError, match="Unsupported setting key"):
        resolve_requested_key("madeupsetting", {})


def test_resolve_requested_key_rejects_ambiguous_normalized_key():
    schema = {
        "map": SettingSpec(
            canonical_key="map",
            aliases=("game-map",),
            description="Current map",
            value_type="string",
        ),
        "game-map": SettingSpec(
            canonical_key="othermap",
            aliases=("game-map",),
            description="Another map",
            value_type="string",
        ),
    }

    with pytest.raises(KeyResolutionError, match="Ambiguous setting key"):
        resolve_requested_key("game-map", schema)


def test_resolve_requested_key_rejects_same_canonical_collision():
    schema = {
        "primary-map": SettingSpec(
            canonical_key="map",
            aliases=("game-map",),
            description="Current map",
            value_type="string",
        ),
        "secondary-map": SettingSpec(
            canonical_key="map",
            aliases=("game-map",),
            description="Backup map",
            value_type="string",
        ),
    }

    with pytest.raises(KeyResolutionError, match="Ambiguous setting key"):
        resolve_requested_key("game-map", schema)


def test_redact_value_hides_secret_values():
    spec = SettingSpec(
        canonical_key="rconpassword",
        aliases=("rconpass",),
        description="Remote console password",
        value_type="string",
        secret=True,
    )

    assert redact_value(spec, "hunter2") == "<redacted>"


@pytest.mark.parametrize("value", [[], {}, ()])
def test_redact_value_does_not_redact_empty_secret_containers(value):
    spec = SettingSpec(
        canonical_key="rconpassword",
        aliases=("rconpass",),
        description="Remote console password",
        value_type="string",
        secret=True,
    )

    assert redact_value(spec, value) == value


def test_build_native_config_values_uses_defaults_and_explicit_native_keys():
    schema = {
        "server_name": SettingSpec(
            canonical_key="servername",
            aliases=("hostname",),
            value_type="string",
            apply_to=("datastore", "native_config"),
            native_config_key="hostname",
        ),
        "slots": SettingSpec(
            canonical_key="maxplayers",
            value_type="integer",
            apply_to=("datastore", "native_config"),
            native_config_key="maxplayers",
        ),
        "map": SettingSpec(
            canonical_key="map",
            value_type="string",
            apply_to=("datastore", "launch_args"),
        ),
    }

    values = build_native_config_values(
        {"maxplayers": "24"},
        schema,
        defaults={"servername": "AlphaGSM"},
        value_transform=lambda spec, value: str(int(value)) if spec.value_type == "integer" else str(value),
        require_explicit_key=True,
    )

    assert values == {"hostname": "AlphaGSM", "maxplayers": "24"}


def test_build_native_config_tree_uses_explicit_nested_paths():
    schema = {
        "bind": SettingSpec(
            canonical_key="bindaddress",
            apply_to=("datastore", "native_config"),
            native_config_path=("a2s", "address"),
        ),
        "query": SettingSpec(
            canonical_key="queryport",
            value_type="integer",
            apply_to=("datastore", "native_config"),
            native_config_path=("a2s", "port"),
        ),
        "slots": SettingSpec(
            canonical_key="maxplayers",
            value_type="integer",
            apply_to=("datastore", "native_config"),
            native_config_path=("game", "maxPlayers"),
        ),
    }

    tree = build_native_config_tree(
        {"bindaddress": "0.0.0.0", "maxplayers": "16"},
        schema,
        defaults={"queryport": 27016},
        value_transform=lambda spec, value: int(value) if spec.value_type == "integer" else str(value),
        require_explicit_path=True,
    )

    assert tree == {
        "a2s": {"address": "0.0.0.0", "port": 27016},
        "game": {"maxPlayers": 16},
    }


def test_merge_nested_config_preserves_unmanaged_nested_fields():
    base = {
        "a2s": {"address": "1.2.3.4", "port": 1111},
        "game": {"admins": ["keep"], "scenarioId": "old"},
    }

    merged = merge_nested_config(
        base,
        {"a2s": {"port": 2222}, "game": {"scenarioId": "new"}},
    )

    assert merged == {
        "a2s": {"address": "1.2.3.4", "port": 2222},
        "game": {"admins": ["keep"], "scenarioId": "new"},
    }


def test_build_launch_arg_values_uses_explicit_tokens_in_schema_order():
    schema = {
        "port": SettingSpec(
            canonical_key="port",
            value_type="integer",
            apply_to=("datastore", "launch_args"),
            launch_arg_tokens=("-port",),
        ),
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap",),
            apply_to=("datastore", "launch_args"),
            storage_key="startmap",
            launch_arg_tokens=("+map",),
        ),
    }

    values = build_launch_arg_values(
        {"port": 27015, "startmap": "cp_badlands"},
        schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )

    assert values == ["-port", "27015", "+map", "cp_badlands"]


def test_build_launch_arg_values_supports_formatted_single_token_args():
    schema = {
        "port": SettingSpec(
            canonical_key="port",
            value_type="integer",
            apply_to=("datastore", "launch_args"),
            launch_arg_format="-port={value}",
        ),
        "query": SettingSpec(
            canonical_key="queryport",
            value_type="integer",
            apply_to=("datastore", "launch_args"),
            launch_arg_format="-queryport={value}",
        ),
    }

    values = build_launch_arg_values(
        {"port": 7777, "queryport": 27015},
        schema,
        value_transform=lambda _spec, value: str(value),
        require_explicit_tokens=True,
    )

    assert values == ["-port=7777", "-queryport=27015"]
