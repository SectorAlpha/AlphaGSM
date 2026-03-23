# Day of Defeat

This guide covers the `dodserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydodserve create dodserver
```

Run setup:

```bash
alphagsm mydodserve setup
```

Start it:

```bash
alphagsm mydodserve start
```

Check it:

```bash
alphagsm mydodserve status
```

Stop it:

```bash
alphagsm mydodserve stop
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
alphagsm mydodserve update
alphagsm mydodserve backup
```

## Notes

- Module name: `dodserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `dod`

### Server Configuration

- **Config file**: `dod/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dod_Anzio`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/dodserver/](../server-templates/dodserver/)

### Maps and Mods

- **Map directory**: `dod/maps/`
- **Mod directory**: `dod/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `dod/maps/` and add to `dod/mapcycle.txt`.
- **Mod install**: Use Metamod in `dod/dlls/` or AMX Mod X in `dod/addons/amxmodx/`.
