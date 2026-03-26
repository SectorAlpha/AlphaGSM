# BrainBread

This guide covers the `bbserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybbserver create bbserver
```

Run setup:

```bash
alphagsm mybbserver setup
```

Start it:

```bash
alphagsm mybbserver start
```

Check it:

```bash
alphagsm mybbserver status
```

Stop it:

```bash
alphagsm mybbserver stop
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
alphagsm mybbserver update
alphagsm mybbserver backup
```

## Notes

- Module name: `bbserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `hlds_run`
- **Location**: `<install_dir>/hlds_run`
- **Engine**: GoldSrc (HLDS)
- **SteamCMD App ID**: `90`
- **Mod App ID**: `cstrike`

### Server Configuration

- **Config file**: `brainbread/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `bb_chp4_slaywatch`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/bbserver/](../server-templates/bbserver/)

### Maps and Mods

- **Map directory**: `brainbread/maps/`
- **Mod directory**: `brainbread/dlls/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `brainbread/maps/` and add to `brainbread/mapcycle.txt`.
- **Mod install**: Use Metamod in `brainbread/dlls/` or AMX Mod X in `brainbread/addons/amxmodx/`.
