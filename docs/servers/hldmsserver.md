# Half-Life Deathmatch: Source

This guide covers the `hldmsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhldmsser create hldmsserver
```

Run setup:

```bash
alphagsm myhldmsser setup
```

Start it:

```bash
alphagsm myhldmsser start
```

Check it:

```bash
alphagsm myhldmsser status
```

Stop it:

```bash
alphagsm myhldmsser stop
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
alphagsm myhldmsser update
alphagsm myhldmsser backup
```

## Notes

- Module name: `hldmsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `255470`

### Server Configuration

- **Config file**: `hl1mp/cfg/server.cfg`
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
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/hldmsserver/](../server-templates/hldmsserver/)

### Maps and Mods

- **Map directory**: `hl1mp/maps/`
- **Mod directory**: `hl1mp/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/hl1mp/`.
- **Map install**: Copy `.bsp` files into `hl1mp/maps/` and add to `hl1mp/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `hl1mp/addons/`.
