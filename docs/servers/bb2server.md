# BrainBread 2

This guide covers the `bb2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybb2serve create bb2server
```

Run setup:

```bash
alphagsm mybb2serve setup
```

Start it:

```bash
alphagsm mybb2serve start
```

Check it:

```bash
alphagsm mybb2serve status
```

Stop it:

```bash
alphagsm mybb2serve stop
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
alphagsm mybb2serve update
alphagsm mybb2serve backup
```

## Notes

- Module name: `bb2server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `475370`

### Server Configuration

- **Config file**: `brainbread2/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `bba_barracks`
- **Max players**: `20`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/bb2server/](../server-templates/bb2server/)

### Maps and Mods

- **Map directory**: `brainbread2/maps/`
- **Mod directory**: `brainbread2/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `brainbread2/maps/` and add to `brainbread2/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `brainbread2/addons/`.
