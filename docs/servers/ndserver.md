# Nuclear Dawn

This guide covers the `ndserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myndserver create ndserver
```

Run setup:

```bash
alphagsm myndserver setup
```

Start it:

```bash
alphagsm myndserver start
```

Check it:

```bash
alphagsm myndserver status
```

Stop it:

```bash
alphagsm myndserver stop
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
alphagsm myndserver update
alphagsm myndserver backup
```

## Notes

- Module name: `ndserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `111710`
- **SteamCMD App Name**: `Nuclear Dawn - Dedicated Server`

### Server Configuration

- **Config file**: `nucleardawn/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `hydro`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/ndserver/](../server-templates/ndserver/)

### Maps and Mods

- **Map directory**: `nucleardawn/maps/`
- **Mod directory**: `nucleardawn/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/nucleardawn/`.
- **Current status**: The anonymous dedicated-server app currently installs only a partial `nucleardawn` tree in CI. It is missing the core game payload needed for a working server, so this module remains disabled until the missing content source is identified.
- **Map install**: Copy `.bsp` files into `nucleardawn/maps/` and add to `nucleardawn/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `nucleardawn/addons/`.
