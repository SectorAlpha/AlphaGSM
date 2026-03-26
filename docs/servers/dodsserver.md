# Day of Defeat: Source

This guide covers the `dodsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydodsserv create dodsserver
```

Run setup:

```bash
alphagsm mydodsserv setup
```

Start it:

```bash
alphagsm mydodsserv start
```

Check it:

```bash
alphagsm mydodsserv status
```

Stop it:

```bash
alphagsm mydodsserv stop
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
alphagsm mydodsserv update
alphagsm mydodsserv backup
```

## Notes

- Module name: `dodsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `232290`

### Server Configuration

- **Config file**: `dod/cfg/server.cfg`
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
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/dodsserver/](../server-templates/dodsserver/)

### Maps and Mods

- **Map directory**: `dod/maps/`
- **Mod directory**: `dod/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `dod/maps/` and add to `dod/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `dod/addons/`.
