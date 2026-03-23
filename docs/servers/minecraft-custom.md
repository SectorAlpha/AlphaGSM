# Common Minecraft

This guide covers the `minecraft.custom` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycustom create minecraft.custom
```

Run setup:

```bash
alphagsm mycustom setup
```

Start it:

```bash
alphagsm mycustom start
```

Check it:

```bash
alphagsm mycustom status
```

Stop it:

```bash
alphagsm mycustom stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mycustom update
alphagsm mycustom backup
```

## Notes

- Module name: `minecraft.custom`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `custom .jar (user-specified)`
- **Location**: `<install_dir>/custom .jar (user-specified)`
- **Engine**: Java (Custom)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-custom/](../server-templates/minecraft-custom/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `mods/ or plugins/ (depends on server type)`
- **Workshop support**: No
- **Map notes**: The world directory contains all world data.
- **Mod notes**: Depends on the custom server type (Forge, Fabric, Spigot, etc.).
