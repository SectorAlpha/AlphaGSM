# Action: Source

This guide covers the `ahl2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myahl2serv create ahl2server
```

Run setup:

```bash
alphagsm myahl2serv setup
```

Start it:

```bash
alphagsm myahl2serv start
```

Check it:

```bash
alphagsm myahl2serv status
```

Stop it:

```bash
alphagsm myahl2serv stop
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
alphagsm myahl2serv update
alphagsm myahl2serv backup
```

## Notes

- Module name: `ahl2server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `985050`

### Server Configuration

- **Config file**: `ahl2/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `act_airport`
- **Max players**: `20`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/ahl2server/](../server-templates/ahl2server/)

### Maps and Mods

- **Map directory**: `ahl2/maps/`
- **Mod directory**: `ahl2/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/ahl2/`.
- **Map install**: Copy `.bsp` files into `ahl2/maps/` and add to `ahl2/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `ahl2/addons/`.
