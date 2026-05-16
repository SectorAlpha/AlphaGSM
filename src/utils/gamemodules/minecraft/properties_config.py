"""Shared config helpers for properties-backed Minecraft server modules."""

from server.settable_keys import SettingSpec, build_native_config_values


CONFIG_SYNC_KEYS = (
    "port",
    "gamemode",
    "difficulty",
    "levelname",
    "maxplayers",
    "servername",
)


def build_setting_schema(
    *,
    port_description,
    port_example,
    map_example,
    maxplayers_example,
    servername_description,
    servername_example,
):
    return {
        "port": SettingSpec(
            canonical_key="port",
            description=port_description,
            value_type="integer",
            apply_to=("datastore", "native_config"),
            native_config_key="server-port",
            examples=(port_example,),
        ),
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "level", "world"),
            description="The selected world or level name.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            storage_key="levelname",
            native_config_key="level-name",
            examples=(map_example,),
        ),
        "gamemode": SettingSpec(
            canonical_key="gamemode",
            description="The default game mode.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            native_config_key="gamemode",
            examples=("survival",),
        ),
        "difficulty": SettingSpec(
            canonical_key="difficulty",
            description="The world difficulty.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            native_config_key="difficulty",
            examples=("easy",),
        ),
        "maxplayers": SettingSpec(
            canonical_key="maxplayers",
            description="The maximum number of players allowed on the server.",
            value_type="integer",
            apply_to=("datastore", "native_config"),
            native_config_key="max-players",
            examples=(maxplayers_example,),
        ),
        "servername": SettingSpec(
            canonical_key="servername",
            description=servername_description,
            value_type="string",
            apply_to=("datastore", "native_config"),
            examples=(servername_example,),
        ),
    }


def build_server_properties_values(
    server,
    *,
    setting_schema,
    servername_key,
    default_port,
    default_levelname,
    default_maxplayers,
    default_servername,
    use_defaults=True,
):
    defaults = None
    if use_defaults:
        defaults = {
            "port": default_port,
            "gamemode": "survival",
            "difficulty": "easy",
            "levelname": default_levelname,
            "maxplayers": default_maxplayers,
            "servername": default_servername,
        }
    else:
        for required_key in (
            "port",
            "gamemode",
            "difficulty",
            "levelname",
            "maxplayers",
            "servername",
        ):
            _ = server.data[required_key]
    return build_native_config_values(
        server.data,
        setting_schema,
        defaults=defaults,
        key_overrides={"servername": servername_key},
        value_transform=lambda spec, value: str(int(value)) if spec.value_type == "integer" else str(value),
        require_explicit_key=True,
    )
