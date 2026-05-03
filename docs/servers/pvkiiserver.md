# Pirates Vikings & Knights II

This guide covers the `pvkiiserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypvkiiser create pvkiiserver
```

Run setup:

```bash
alphagsm mypvkiiser setup
```

Start it:

```bash
alphagsm mypvkiiser start
```

Check it:

```bash
alphagsm mypvkiiser status
```

Stop it:

```bash
alphagsm mypvkiiser stop
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
alphagsm mypvkiiser update
alphagsm mypvkiiser backup
```

## Notes

- Module name: `pvkiiserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `17575`

### Server Configuration

- **Config file**: `pvkii/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `bt_island`
- **Max players**: `24`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/pvkiiserver/](../server-templates/pvkiiserver/)

### Maps and Mods

- **Map directory**: `pvkii/maps/`
- **Mod directory**: `pvkii/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/pvkii/`.
- **Map install**: Copy `.bsp` files into `pvkii/maps/` and add to `pvkii/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `pvkii/addons/`.
