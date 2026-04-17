"""Shared config helpers for properties-backed Minecraft server modules."""

from server.settable_keys import SettingSpec


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
            examples=(port_example,),
        ),
        "map": SettingSpec(
            canonical_key="map",
            aliases=("gamemap", "level", "world"),
            description="The selected world or level name.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            storage_key="levelname",
            examples=(map_example,),
        ),
        "gamemode": SettingSpec(
            canonical_key="gamemode",
            description="The default game mode.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            examples=("survival",),
        ),
        "difficulty": SettingSpec(
            canonical_key="difficulty",
            description="The world difficulty.",
            value_type="string",
            apply_to=("datastore", "native_config"),
            examples=("easy",),
        ),
        "maxplayers": SettingSpec(
            canonical_key="maxplayers",
            description="The maximum number of players allowed on the server.",
            value_type="integer",
            apply_to=("datastore", "native_config"),
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
    servername_key,
    default_port,
    default_levelname,
    default_maxplayers,
    default_servername,
):
    return {
        "server-port": str(int(server.data.get("port", default_port))),
        "gamemode": str(server.data.get("gamemode", "survival")),
        "difficulty": str(server.data.get("difficulty", "easy")),
        "level-name": str(server.data.get("levelname", default_levelname)),
        "max-players": str(server.data.get("maxplayers", default_maxplayers)),
        servername_key: str(server.data.get("servername", default_servername)),
    }
