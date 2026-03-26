# Left 4 Dead 2

This guide covers the `l4d2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myl4d2serv create l4d2server
```

Run setup:

```bash
alphagsm myl4d2serv setup
```

Start it:

```bash
alphagsm myl4d2serv start
```

Check it:

```bash
alphagsm myl4d2serv status
```

Stop it:

```bash
alphagsm myl4d2serv stop
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
alphagsm myl4d2serv update
alphagsm myl4d2serv backup
```

## Notes

- Module name: `l4d2server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `222860`

### Server Configuration

- **Config file**: `left4dead2/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `c5m1_waterfront`
- **Max players**: `8`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
- **Template**: See [server-templates/l4d2server/](../server-templates/l4d2server/)

### Maps and Mods

- **Map directory**: `left4dead2/maps/`
- **Mod directory**: `left4dead2/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `left4dead2/maps/` and add to `left4dead2/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `left4dead2/addons/`.
