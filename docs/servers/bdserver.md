# Base Defense

This guide covers the `bdserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybdserver create bdserver
```

Run setup:

```bash
alphagsm mybdserver setup
```

Start it:

```bash
alphagsm mybdserver start
```

Check it:

```bash
alphagsm mybdserver status
```

Stop it:

```bash
alphagsm mybdserver stop
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
alphagsm mybdserver update
alphagsm mybdserver backup
```

## Notes

- Module name: `bdserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `817300`

### Server Configuration

- **Config file**: `bdef/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `pve_tomb`
- **Max players**: `3`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/bdserver/](../server-templates/bdserver/)

### Maps and Mods

- **Map directory**: `bdef/maps/`
- **Mod directory**: `bdef/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `bdef/maps/` and add to `bdef/mapcycle.txt`.
- **Mod install**: Use Metamod in `bdef/dlls/` or AMX Mod X in `bdef/addons/amxmodx/`.
