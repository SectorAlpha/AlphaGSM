# Minecraft Bedrock Edition

This guide covers the `minecraft.bedrock` module in AlphaGSM.

`minecraft.bedrock` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. The current GitHub integration lane still exercises both
process and Docker runtime selection, but the validated anonymous Linux path
remains Docker-first through the shared `service-console` runtime family while
local process mode still depends on the host Bedrock libraries being present.

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

## Resetting the World

Stop the server, then run `alphagsm mymc reset-world` (or `wipe`). AlphaGSM
lists the world data to delete and asks for confirmation. Add `-Y` to skip the
prompt. Run `start` afterwards to generate a fresh world.

See [world creation and reset](../world-management.md) for exactly which files
are removed and the supported layouts.

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

<!-- alphagsm-server-variables:start -->

## Server variables

After `create minecraft.bedrock`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

| Key | Aliases | Type | What it does |
| --- | --- | --- | --- |
| `difficulty` | — | string | The world difficulty. Example: `easy`. |
| `gamemode` | — | string | The default game mode. Example: `survival`. |
| `map` | gamemap, level, world, startmap, worldname | string | The selected world or level name. Example: `Bedrock level`. |
| `maxplayers` | users | integer | The maximum number of players allowed on the server. Example: `10`. |
| `port` | gameport | integer | The port the Bedrock server listens on. Example: `19132`. |
| `servername` | hostname, name | string | The server name shown in Bedrock server listings. Example: `AlphaGSM Bedrock Server`. |

<!-- alphagsm-server-variables:end -->

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
