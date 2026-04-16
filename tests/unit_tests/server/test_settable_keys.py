from server.settable_keys import (
    KeyResolutionError,
    SettingSpec,
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
