# minecraft.waterfall

This guide covers the `minecraft.waterfall` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywaterfal create minecraft.waterfall
```

Run setup:

```bash
alphagsm mywaterfal setup
```

Start it:

```bash
alphagsm mywaterfal start
```

Check it:

```bash
alphagsm mywaterfal status
```

Stop it:

```bash
alphagsm mywaterfal stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Useful Commands

```bash
alphagsm mywaterfal update
alphagsm mywaterfal backup
```

## Notes

- Module name: `minecraft.waterfall`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `waterfall.jar`
- **Location**: `<install_dir>/waterfall.jar`
- **Engine**: Java (Waterfall proxy)

### Server Configuration

- **Config file**: `config.yml`
- **Key settings** (in `config.yml`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-waterfall/](../server-templates/minecraft-waterfall/) if available

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: Waterfall is a proxy and does not host worlds.
- **Mod notes**: Place Waterfall plugin .jar files in the `plugins/` directory.
