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
