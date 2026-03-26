# Deathmatch Classic

This guide covers the `dmcserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydmcserve create dmcserver
```

Run setup:

```bash
alphagsm mydmcserve setup
```

Start it:

```bash
alphagsm mydmcserve start
```

Check it:

```bash
alphagsm mydmcserve status
```

Stop it:

```bash
alphagsm mydmcserve stop
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
alphagsm mydmcserve update
alphagsm mydmcserve backup
```

## Notes

- Module name: `dmcserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `dmc`

### Server Configuration

- **Config file**: `dmc/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dcdm5`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/dmcserver/](../server-templates/dmcserver/)

### Maps and Mods

- **Map directory**: `dmc/maps/`
- **Mod directory**: `dmc/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `dmc/maps/` and add to `dmc/mapcycle.txt`.
- **Mod install**: Use Metamod in `dmc/dlls/` or AMX Mod X in `dmc/addons/amxmodx/`.
