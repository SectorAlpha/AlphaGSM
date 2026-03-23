# Team Fortress Classic

This guide covers the `tfcserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mytfcserve create tfcserver
```

Run setup:

```bash
alphagsm mytfcserve setup
```

Start it:

```bash
alphagsm mytfcserve start
```

Check it:

```bash
alphagsm mytfcserve status
```

Stop it:

```bash
alphagsm mytfcserve stop
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
alphagsm mytfcserve update
alphagsm mytfcserve backup
```

## Notes

- Module name: `tfcserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `tfc`

### Server Configuration

- **Config file**: `tfc/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dustbowl`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/tfcserver/](../server-templates/tfcserver/)

### Maps and Mods

- **Map directory**: `tfc/maps/`
- **Mod directory**: `tfc/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `tfc/maps/` and add to `tfc/mapcycle.txt`.
- **Mod install**: Use Metamod in `tfc/dlls/` or AMX Mod X in `tfc/addons/amxmodx/`.
