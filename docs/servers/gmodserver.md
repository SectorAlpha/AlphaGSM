# Garrys Mod

This guide covers the `gmodserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygmodserv create gmodserver
```

Run setup:

```bash
alphagsm mygmodserv setup
```

Start it:

```bash
alphagsm mygmodserv start
```

Check it:

```bash
alphagsm mygmodserv status
```

Stop it:

```bash
alphagsm mygmodserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- SteamCMD also downloads common mountable Source content into `_gmod_content/`
- default configuration and backup settings

## Useful Commands

```bash
alphagsm mygmodserv update
alphagsm mygmodserv backup
```

## Notes

- Module name: `gmodserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `4020`

### Server Configuration

- **Config file**: `garrysmod/cfg/server.cfg`
- **Mount config**: `garrysmod/cfg/mount.cfg`
- **Depot config**: `garrysmod/cfg/mountdepots.txt`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `gm_construct`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/gmodserver/](../server-templates/gmodserver/)

### Maps and Mods

- **Map directory**: `garrysmod/maps/`
- **Mod directory**: `garrysmod/addons/`
- **Mounted base content**: AlphaGSM installs common Source content under `_gmod_content/`
  and writes default mounts for Counter-Strike: Source, Half-Life 2: Deathmatch,
  and Team Fortress 2.
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `garrysmod/maps/` and add to `garrysmod/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `garrysmod/addons/`.

### Extra Content Notes

- Facepunch recommends installing extra mounted content outside the server root; AlphaGSM follows that pattern with `_gmod_content/`.
- `mountdepots.txt` is seeded with the default Garry's Mod depot set, including `hl1`, `hl1_hd`, `hl2`, `episodic`, `ep2`, and `lostcoast`.
- Single-player Valve games such as Episode One, Episode Two, and Lost Coast still require an owned Steam account if you want to download their content manually.
