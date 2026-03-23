# Fistful of Frags

This guide covers the `fofserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfofserve create fofserver
```

Run setup:

```bash
alphagsm myfofserve setup
```

Start it:

```bash
alphagsm myfofserve start
```

Check it:

```bash
alphagsm myfofserve status
```

Stop it:

```bash
alphagsm myfofserve stop
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
alphagsm myfofserve update
alphagsm myfofserve backup
```

## Notes

- Module name: `fofserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `295230`

### Server Configuration

- **Config file**: `fof/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `fof_depot`
- **Max players**: `20`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/fofserver/](../server-templates/fofserver/)

### Maps and Mods

- **Map directory**: `fof/maps/`
- **Mod directory**: `fof/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `fof/maps/` and add to `fof/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `fof/addons/`.
