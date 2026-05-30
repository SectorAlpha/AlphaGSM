# Minecraft Bedrock Edition

This guide covers the `minecraft.bedrock` module in AlphaGSM.

## Requirements

- Docker is recommended on Linux; AlphaGSM can run Bedrock through the shared `service-console` runtime image.
- For local process mode, install `screen` and the Bedrock shared-library dependencies, including `libcurl.so.4`.
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybedrock create minecraft.bedrock
```

Run setup:

```bash
alphagsm mybedrock setup
```

Start it:

```bash
alphagsm mybedrock start
```

Check it:

```bash
alphagsm mybedrock status
```

Stop it:

```bash
alphagsm mybedrock stop
```

## Setup Details

Setup configures:

- the game port (default 19132)
- the install directory

## Useful Commands

```bash
alphagsm mybedrock update
alphagsm mybedrock backup
alphagsm mybedrock set gamemap BedrockWorld
alphagsm mybedrock set servername "AlphaGSM Bedrock Server"
```

## Notes

- Module name: `minecraft.bedrock`
- Default port: 19132
- Fresh Docker-backed support was revalidated on 2026-05-30 with `query`, `info`, `info --json`, and clean stop all passing on the shared `service-console` runtime family.

## Developer Notes

### Run File

- **Executable**: `bedrock_server`
- **Location**: `<install_dir>/bedrock_server`
- **Engine**: Bedrock (C++)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 19132)
  - `level-name` — World name managed by `set gamemap`
  - `server-name` — Server name managed by `set servername`
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-bedrock/](../server-templates/minecraft-bedrock/) if available

### Maps and Mods

- **Map directory**: `worlds/`
- **Mod directory**: `behavior_packs/ and resource_packs/`
- **Workshop support**: No
- **Map notes**: World data is in the `worlds/` directory.
- **Mod notes**: Place packs in the appropriate directory and reference them in `worlds/<world>/world_behavior_packs.json`.
