This directory includes Interstellar Rift's runtime server config example.

Use `server.json` as the native Interstellar Rift config file.
On Windows, the upstream dedicated-server guide places it under `%APPDATA%/InterstellarRift/`; Wine or Proton installs use the equivalent appdata path inside the prefix.
AlphaGSM still manages the listen port through the launch command, and the repo does not currently model the full `server.json` schema.
