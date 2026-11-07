This directory includes Enshrouded's runtime server config example.

Use `enshrouded_server.json` in the install root for native Enshrouded server settings.
AlphaGSM manages `name` and `queryPort` in this file. The current server uses the managed game port as its query port by default (`15637`).
AlphaGSM still manages the save-name launch argument through the module datastore and start command.
Freshly generated Enshrouded configs may also include `password` and `userGroups` sections with randomized passwords; those values are runtime-generated rather than stable deterministic defaults.
