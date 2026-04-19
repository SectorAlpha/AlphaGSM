from types import SimpleNamespace

import utils.gamemodules.minecraft.properties_config as properties_config


def test_build_setting_schema_uses_shared_map_aliases_and_levelname_storage():
    schema = properties_config.build_setting_schema(
        port_description="The port the Bedrock server listens on.",
        port_example="19132",
        map_example="Bedrock level",
        maxplayers_example="10",
        servername_description="The server name shown in Bedrock server listings.",
        servername_example="AlphaGSM Bedrock Server",
    )

    assert properties_config.CONFIG_SYNC_KEYS == (
        "port",
        "gamemode",
        "difficulty",
        "levelname",
        "maxplayers",
        "servername",
    )
    assert schema["port"].native_config_key == "server-port"
    assert schema["map"].aliases == ("gamemap", "level", "world")
    assert schema["map"].storage_key == "levelname"
    assert schema["map"].native_config_key == "level-name"
    assert schema["servername"].canonical_key == "servername"


def test_build_server_properties_values_switches_servername_target_key():
    server = SimpleNamespace(
        name="alpha",
        data={
            "port": 19132,
            "gamemode": "creative",
            "difficulty": "hard",
            "levelname": "alpha_world",
            "maxplayers": "12",
            "servername": "AlphaGSM Alpha",
        },
    )

    bedrock_values = properties_config.build_server_properties_values(
        server,
        setting_schema=properties_config.build_setting_schema(
            port_description="The port the Bedrock server listens on.",
            port_example="19132",
            map_example="Bedrock level",
            maxplayers_example="10",
            servername_description="The server name shown in Bedrock server listings.",
            servername_example="AlphaGSM Bedrock Server",
        ),
        servername_key="server-name",
        default_port=19132,
        default_levelname=server.name,
        default_maxplayers="10",
        default_servername="AlphaGSM %s" % (server.name,),
    )
    custom_values = properties_config.build_server_properties_values(
        server,
        setting_schema=properties_config.build_setting_schema(
            port_description="The port the server listens on.",
            port_example="25565",
            map_example="world",
            maxplayers_example="20",
            servername_description="The server name shown in the client list.",
            servername_example="AlphaGSM Server",
        ),
        servername_key="motd",
        default_port=25565,
        default_levelname=server.name,
        default_maxplayers="20",
        default_servername="AlphaGSM %s" % (server.name,),
    )

    assert bedrock_values["server-name"] == "AlphaGSM Alpha"
    assert "motd" not in bedrock_values
    assert custom_values["motd"] == "AlphaGSM Alpha"
    assert "server-name" not in custom_values
