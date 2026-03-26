# No More Room in Hell

This guide covers the `nmrihserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynmrihser create nmrihserver
```

Run setup:

```bash
alphagsm mynmrihser setup
```

Start it:

```bash
alphagsm mynmrihser start
```

Check it:

```bash
alphagsm mynmrihser status
```

Stop it:

```bash
alphagsm mynmrihser stop
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
alphagsm mynmrihser update
alphagsm mynmrihser backup
```

## Notes

- Module name: `nmrihserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `317670`

### Server Configuration

- **Config file**: `nmrih/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `nmo_broadway`
- **Max players**: `8`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/nmrihserver/](../server-templates/nmrihserver/)

### Maps and Mods

- **Map directory**: `nmrih/maps/`
- **Mod directory**: `nmrih/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `nmrih/maps/` and add to `nmrih/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `nmrih/addons/`.
