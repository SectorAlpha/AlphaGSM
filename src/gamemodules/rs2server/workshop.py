"""Rising Storm 2 native server Workshop subscriptions and client delivery."""
from gamemodules.kf2server.workshop import configure_native_workshop


def configure_workshop(server, item_ids):
    """Activate RS2 subscriptions without claiming the engine download cache."""
    return configure_native_workshop(
        server, item_ids, relative="ROGame/Config/PCServer-ROEngine.ini",
        section="OnlineSubsystemSteamworks.TWWorkshopSteamworks", owner="rs2_workshop",
    )
