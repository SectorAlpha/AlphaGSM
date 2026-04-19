This directory includes Enshrouded's runtime server config example.

Use `enshrouded_server.json` in the install root for native Enshrouded server settings.
AlphaGSM still manages the separate game port and save-name launch arguments through the module datastore and start command.
Freshly generated Enshrouded configs may also include `password` and `userGroups` sections with randomized passwords; those values are runtime-generated rather than stable deterministic defaults.
