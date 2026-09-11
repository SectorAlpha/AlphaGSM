Use this directory as the seed when creating a new server-template entry.

Filename rule:
- If the module or server guide identifies one stable runtime config file, name the example after that exact file and keep the same relative path if it matters.
- If the module only exposes AlphaGSM-managed values and does not own one stable runtime config filename, keep the example as alphagsm-example.cfg.

Content rule:
- Include concrete defaults from configure(), sync_server_config(), smoke tests, or docs/servers/<module>.md.
- Make the file look like the real server config: same key names, same syntax style, similar comments, and similar section structure.
- Include every practical game-facing key AlphaGSM exposes for the module.
- Omit AlphaGSM-only datastore fields such as download_name, dir, backup, image, or other manager metadata.

Copy the closer seed below, then rename it to the game's real filename when evidence exists.