# Double Action: Boogaloo

This guide covers the `dabserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydabserve create dabserver
```

Run setup:

```bash
alphagsm mydabserve setup
```

Start it:

```bash
alphagsm mydabserve start
```

Check it:

```bash
alphagsm mydabserve status
```

Stop it:

```bash
alphagsm mydabserve stop
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
alphagsm mydabserve update
alphagsm mydabserve backup
```

## Notes

- Module name: `dabserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `dabds.sh`
- **Location**: `<install_dir>/dabds.sh`
- **Engine**: Source
- **SteamCMD App ID**: `317800`

### Server Configuration

- **Config file**: `dab/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `da_rooftops`
- **Max players**: `10`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/dabserver/](../server-templates/dabserver/)

### Maps and Mods

- **Map directory**: `dab/maps/`
- **Mod directory**: `dab/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `dab/maps/` and add to `dab/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `dab/addons/`.
