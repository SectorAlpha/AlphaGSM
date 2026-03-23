# Counter-Strike: Source

This guide covers the `cssserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycssserve create cssserver
```

Run setup:

```bash
alphagsm mycssserve setup
```

Start it:

```bash
alphagsm mycssserve start
```

Check it:

```bash
alphagsm mycssserve status
```

Stop it:

```bash
alphagsm mycssserve stop
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
alphagsm mycssserve update
alphagsm mycssserve backup
```

## Notes

- Module name: `cssserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `232330`

### Server Configuration

- **Config file**: `cstrike/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `de_dust2`
- **Max players**: `16`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/cssserver/](../server-templates/cssserver/)

### Maps and Mods

- **Map directory**: `cstrike/maps/`
- **Mod directory**: `cstrike/addons/`
- **Workshop support**: No
- **Map install**: Copy `.bsp` files into `cstrike/maps/` and add to `cstrike/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `cstrike/addons/`.
