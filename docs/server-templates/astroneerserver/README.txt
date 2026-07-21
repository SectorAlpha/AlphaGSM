This directory includes a config example for this server.

Use the included file as a starting point for the values AlphaGSM exposes through setup, set, and start.
If the filename matches the game's real runtime config, use it directly. If the file is named alphagsm-example.cfg, treat it as an AlphaGSM-oriented reference and translate those values into the game's own config layout or generated files as needed.

AlphaGSM also writes net.AllowEncryption=False under [SystemSettings] in the
game-owned Astro/Saved/Config/WindowsServer/Engine.ini. This keeps the supported
Wine/Proton server path compatible with joining clients configured the same way.
