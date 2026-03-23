# minecraft.paper

This guide covers the `minecraft.paper` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypaper create minecraft.paper
```

Run setup:

```bash
alphagsm mypaper setup
```

Start it:

```bash
alphagsm mypaper start
```

Check it:

```bash
alphagsm mypaper status
```

Stop it:

```bash
alphagsm mypaper stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Useful Commands

```bash
alphagsm mypaper update
alphagsm mypaper backup
```

## Notes

- Module name: `minecraft.paper`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `paper.jar`
- **Location**: `<install_dir>/paper.jar`
- **Engine**: Java (PaperMC)

### Server Configuration

- **Config file**: `server.properties`
- **Key settings** (in `server.properties`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-paper/](../server-templates/minecraft-paper/) if available

### Maps and Mods

- **Map directory**: `world/`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: The world directory contains all world data. Delete it to regenerate.
- **Mod notes**: Place plugin .jar files in the `plugins/` directory and restart.
