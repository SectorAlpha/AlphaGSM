Stormworks uses server_config.xml plus runtime-generated dedicated-server state.
This module knows the core launch defaults but does not currently synthesize the
full Stormworks XML schema from datastore values.

Module-known defaults:
- port: 25565
- queryport: 25566
- configfile: server_config.xml
- exe_name: server64.exe

Use the game's generated XML as the authoritative base and then align the port
and query port with AlphaGSM's configured values.