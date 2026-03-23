# Opposing Force

This guide covers the `opforserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myopforser create opforserver
```

Run setup:

```bash
alphagsm myopforser setup
```

Start it:

```bash
alphagsm myopforser start
```

Check it:

```bash
alphagsm myopforser status
```

Stop it:

```bash
alphagsm myopforser stop
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
alphagsm myopforser update
alphagsm myopforser backup
```

## Notes

- Module name: `opforserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `gearbox`

### Server Configuration

- **Config file**: `gearbox/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `op4_bootcamp`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/opforserver/](../server-templates/opforserver/)

### Maps and Mods

- **Map directory**: `gearbox/maps/`
- **Mod directory**: `gearbox/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `gearbox/maps/` and add to `gearbox/mapcycle.txt`.
- **Mod install**: Use Metamod in `gearbox/dlls/` or AMX Mod X in `gearbox/addons/amxmodx/`.
