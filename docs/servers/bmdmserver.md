# Black Mesa: Deathmatch

This guide covers the `bmdmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybmdmserv create bmdmserver
```

Run setup:

```bash
alphagsm mybmdmserv setup
```

Start it:

```bash
alphagsm mybmdmserv start
```

Check it:

```bash
alphagsm mybmdmserv status
```

Stop it:

```bash
alphagsm mybmdmserv stop
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
alphagsm mybmdmserv update
alphagsm mybmdmserv backup
```

## Notes

- Module name: `bmdmserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `346680`

### Server Configuration

- **Config file**: `bms/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dm_bounce`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/bmdmserver/](../server-templates/bmdmserver/)

### Maps and Mods

- **Map directory**: `bms/maps/`
- **Mod directory**: `bms/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/bms/`.
- **Map install**: Copy `.bsp` files into `bms/maps/` and add to `bms/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `bms/addons/`.
