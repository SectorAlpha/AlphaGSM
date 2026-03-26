# Zombie Panic! Source

This guide covers the `zpsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myzpsserve create zpsserver
```

Run setup:

```bash
alphagsm myzpsserve setup
```

Start it:

```bash
alphagsm myzpsserve start
```

Check it:

```bash
alphagsm myzpsserve status
```

Stop it:

```bash
alphagsm myzpsserve stop
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
alphagsm myzpsserve update
alphagsm myzpsserve backup
```

## Notes

- Module name: `zpsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `17505`

### Server Configuration

- **Config file**: `zps/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `zps_deadend`
- **Max players**: `20`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/zpsserver/](../server-templates/zpsserver/)

### Maps and Mods

- **Map directory**: `zps/maps/`
- **Mod directory**: `zps/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `zps/maps/` and add to `zps/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `zps/addons/`.
