# Zombie Master: Reborn

This guide covers the `zmrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- Manual Zombie Master: Reborn server content; SteamCMD app `244310` only installs `Source SDK Base 2013 Dedicated Server`

## Quick Start

Create the server:

```bash
alphagsm myzmrserve create zmrserver
```

Run setup:

```bash
alphagsm myzmrserve setup
```

Start it:

```bash
alphagsm myzmrserve start
```

Check it:

```bash
alphagsm myzmrserve status
```

Stop it:

```bash
alphagsm myzmrserve stop
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
alphagsm myzmrserve update
alphagsm myzmrserve backup
```

## Notes

- Module name: `zmrserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `244310`
- **SteamCMD App Name**: `Source SDK Base 2013 Dedicated Server`

### Server Configuration

- **Config file**: `zombie_master_reborn/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `zm_docksofthedead`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/zmrserver/](../server-templates/zmrserver/)

### Maps and Mods

- **Map directory**: `zombie_master_reborn/maps/`
- **Mod directory**: `zombie_master_reborn/addons/`
- **Workshop support**: No
- **Current status**: Anonymous SteamCMD only provides the generic Source SDK 2013 dedicated server scaffold. It does not include the `zombie_master_reborn` mod payload, so this module remains disabled until a real content source or additional install step is implemented.
- **Map install**: Copy `.bsp` files into `zombie_master_reborn/maps/` and add to `zombie_master_reborn/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `zombie_master_reborn/addons/`.
