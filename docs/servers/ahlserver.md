# Action Half-Life

This guide covers the `ahlserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myahlserve create ahlserver
```

Run setup:

```bash
alphagsm myahlserve setup
```

Start it:

```bash
alphagsm myahlserve start
```

Check it:

```bash
alphagsm myahlserve status
```

Stop it:

```bash
alphagsm myahlserve stop
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
alphagsm myahlserve update
alphagsm myahlserve backup
```

## Notes

- Module name: `ahlserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `action/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `ahl_hydro`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/ahlserver/](../server-templates/ahlserver/)

### Maps and Mods

- **Map directory**: `action/maps/`
- **Mod directory**: `action/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `action/maps/` and add to `action/mapcycle.txt`.
- **Mod install**: Use Metamod in `action/dlls/` or AMX Mod X in `action/addons/amxmodx/`.
