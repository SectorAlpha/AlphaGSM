# Codename CURE

This guide covers the `ccserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myccserver create ccserver
```

Run setup:

```bash
alphagsm myccserver setup
```

Start it:

```bash
alphagsm myccserver start
```

Check it:

```bash
alphagsm myccserver status
```

Stop it:

```bash
alphagsm myccserver stop
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
alphagsm myccserver update
alphagsm myccserver backup
```

## Notes

- Module name: `ccserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `383410`

### Server Configuration

- **Config file**: `cure/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `cbe_bunker`
- **Max players**: `6`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/ccserver/](../server-templates/ccserver/)

### Maps and Mods

- **Map directory**: `cure/maps/`
- **Mod directory**: `cure/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/cure/`.
- **Map install**: Copy `.bsp` files into `cure/maps/` and add to `cure/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `cure/addons/`.
