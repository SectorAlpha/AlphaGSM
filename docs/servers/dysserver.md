# Dystopia

This guide covers the `dysserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydysserve create dysserver
```

Run setup:

```bash
alphagsm mydysserve setup
```

Start it:

```bash
alphagsm mydysserve start
```

Check it:

```bash
alphagsm mydysserve status
```

Stop it:

```bash
alphagsm mydysserve stop
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
alphagsm mydysserve update
alphagsm mydysserve backup
```

## Notes

- Module name: `dysserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run.sh`
- **Location**: `<install_dir>/srcds_run.sh`
- **Engine**: Source
- **SteamCMD App ID**: `17585`

### Server Configuration

- **Config file**: `dystopia/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `dys_broadcast`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/dysserver/](../server-templates/dysserver/)

### Maps and Mods

- **Map directory**: `dystopia/maps/`
- **Mod directory**: `dystopia/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `dystopia/maps/` and add to `dystopia/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `dystopia/addons/`.
