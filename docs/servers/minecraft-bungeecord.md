# Collect and store configuration values for a Bungeecord

This guide covers the `minecraft.bungeecord` module in AlphaGSM.

## Requirements

- `screen`
- Java 21 or compatible runtime
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybungeeco create minecraft.bungeecord
```

Run setup:

```bash
alphagsm mybungeeco setup
```

Start it:

```bash
alphagsm mybungeeco start
```

Check it:

```bash
alphagsm mybungeeco status
```

Stop it:

```bash
alphagsm mybungeeco stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory

## Useful Commands

```bash
alphagsm mybungeeco update
alphagsm mybungeeco backup
```

## Notes

- Module name: `minecraft.bungeecord`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `BungeeCord.jar`
- **Location**: `<install_dir>/BungeeCord.jar`
- **Engine**: Java (BungeeCord proxy)

### Server Configuration

- **Config file**: `config.yml`
- **Key settings** (in `config.yml`):
  - `server-port` — Game port (default 25565)
  - `motd` — Message of the day
  - `max-players` — Maximum players
  - `level-seed` — World generation seed
  - `online-mode` — Mojang authentication
- **Template**: See [server-templates/minecraft-bungeecord/](../server-templates/minecraft-bungeecord/) if available

### Maps and Mods

- **Map directory**: `N/A (proxy)`
- **Mod directory**: `plugins/`
- **Workshop support**: No
- **Map notes**: BungeeCord is a proxy and does not host worlds.
- **Mod notes**: Place BungeeCord plugin .jar files in the `plugins/` directory.
