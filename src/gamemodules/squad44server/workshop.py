"""Squad 44's game identity and native Unreal plugin destination."""

from gamemodules.squadserver.workshop import configure_plugin_workshop


def configure_workshop(server, item_ids):
    """Stage Squad 44 plugins using its distinct consumer AppID and game root."""
    return configure_plugin_workshop(server, 736220, "PostScriptum", "squad44_workshop", item_ids)
