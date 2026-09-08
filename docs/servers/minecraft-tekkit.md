# Resolve the direct

This guide covers the `minecraft.tekkit` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytekkit create minecraft.tekkit
```

Run setup:

```bash
alphagsm mytekkit setup
```

`minecraft.tekkit` is supported in `ENABLED (BYO)` mode. The old automatic
TechnicPack page scrape is no longer reliable, so before `setup` or `start`
you should either:

- set `url` to a direct Tekkit server archive URL, or
- stage `Tekkit.jar` directly inside `<install_dir>/`

Start it:

```bash
alphagsm mytekkit start
```

Check it:

```bash
alphagsm mytekkit status
```

Stop it:

```bash
alphagsm mytekkit stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

Suggested flow:

```bash
alphagsm mytekkit create minecraft.tekkit
alphagsm mytekkit setup -n 25565 /path/to/minecraft-tekkit --url https://example.com/Tekkit.zip
alphagsm mytekkit start
```

Or with a pre-staged jar:

```bash
alphagsm mytekkit create minecraft.tekkit
alphagsm mytekkit setup -n 25565 /path/to/minecraft-tekkit
# place Tekkit.jar in /path/to/minecraft-tekkit/
alphagsm mytekkit start
```

## Resetting the World

Stop the server, then run `alphagsm mymc reset-world` (or `wipe`). AlphaGSM
lists the world data to delete and asks for confirmation. Add `-Y` to skip the
prompt. Run `start` afterwards to generate a fresh world.

See [world creation and reset](../world-management.md) for exactly which files
are removed and the supported layouts.

## Useful Commands

```bash
alphagsm mytekkit update
alphagsm mytekkit backup
```

## Notes

- Module name: `minecraft.tekkit`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Tekkit.jar / custom jar`
- **Location**: `<install_dir>/Tekkit.jar / custom jar`
- **Engine**: Java (Tekkit modpack)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-tekkit/](../server-templates/minecraft-tekkit/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `mods/`
- **Workshop support**: No
- **Map notes**: The world directory contains all world data.
- **Mod notes**: Tekkit ships with pre-configured mods. Additional mods go in `mods/`.
