# minecraft.velocity

This guide covers the `minecraft.velocity` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvelocity create minecraft.velocity
```

Run setup:

```bash
alphagsm myvelocity setup
```

Start it:

```bash
alphagsm myvelocity start
```

Check it:

```bash
alphagsm myvelocity status
```

Stop it:

```bash
alphagsm myvelocity stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory

## Useful Commands

```bash
alphagsm myvelocity update
alphagsm myvelocity backup
```

## Notes

- Module name: `minecraft.velocity`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `velocity.jar`
- **Location**: `<install_dir>/velocity.jar`
- **Engine**: Java (Velocity proxy)

### Server Configuration

- **Config file**: `velocity.toml`
- **Key settings** (in `velocity.toml`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-velocity/](../server-templates/minecraft-velocity/) if available

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: Velocity is a proxy and does not host worlds.
- **Mod notes**: Place Velocity plugin .jar files in the `plugins/` directory.
