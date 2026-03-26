# Empires Mod

This guide covers the `emserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myemserver create emserver
```

Run setup:

```bash
alphagsm myemserver setup
```

Start it:

```bash
alphagsm myemserver start
```

Check it:

```bash
alphagsm myemserver status
```

Stop it:

```bash
alphagsm myemserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

## Useful Commands

```bash
alphagsm myemserver update
alphagsm myemserver backup
```

## Notes

- Module name: `emserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `460040`

### Server Configuration

- **Config file**: `empires/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `con_district402`
- **Max players**: `62`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/emserver/](../server-templates/emserver/)

### Maps and Mods

- **Map directory**: `empires/maps/`
- **Mod directory**: `empires/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `empires/maps/` and add to `empires/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `empires/addons/`.
