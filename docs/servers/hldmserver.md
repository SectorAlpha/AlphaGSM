# Half-Life: Deathmatch

This guide covers the `hldmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhldmserv create hldmserver
```

Run setup:

```bash
alphagsm myhldmserv setup
```

Start it:

```bash
alphagsm myhldmserv start
```

Check it:

```bash
alphagsm myhldmserv status
```

Stop it:

```bash
alphagsm myhldmserv stop
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
alphagsm myhldmserv update
alphagsm myhldmserv backup
```

## Notes

- Module name: `hldmserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`

### Server Configuration

- **Config file**: `valve/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `crossfire`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/hldmserver/](../server-templates/hldmserver/)

### Maps and Mods

- **Map directory**: `valve/maps/`
- **Mod directory**: `valve/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `valve/maps/` and add to `valve/mapcycle.txt`.
- **Mod install**: Use Metamod in `valve/dlls/` or AMX Mod X in `valve/addons/amxmodx/`.
