# Blade Symphony

This guide covers the `bsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybsserver create bsserver
```

Run setup:

```bash
alphagsm mybsserver setup
```

Start it:

```bash
alphagsm mybsserver start
```

Check it:

```bash
alphagsm mybsserver status
```

Stop it:

```bash
alphagsm mybsserver stop
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
alphagsm mybsserver update
alphagsm mybsserver backup
```

## Notes

- Module name: `bsserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run.sh`
- **Location**: `<install_dir>/srcds_run.sh`
- **Engine**: Source
- **SteamCMD App ID**: `228780`

### Server Configuration

- **Config file**: `berimbau/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `duel_winter`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/bsserver/](../server-templates/bsserver/)

### Maps and Mods

- **Map directory**: `berimbau/maps/`
- **Mod directory**: `berimbau/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `berimbau/maps/` and add to `berimbau/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `berimbau/addons/`.
