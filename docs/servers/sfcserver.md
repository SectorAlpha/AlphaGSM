# SourceForts Classic

This guide covers the `sfcserver` module in AlphaGSM.

`sfcserver` is currently `ENABLED (BYO)` on the documented Ubuntu 24.04 Linux
baseline. The current GitHub integration lane still exercises both process and
Docker runtime selection around that staged-ModDB-content prerequisite, while
local runs remain process-backed by default unless you opt into the Docker
backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`
- An official SourceForts Classic full-version archive from ModDB, extracted under `<install_dir>/sfclassic/`

## Support Status

`sfcserver` is supported in `ENABLED (BYO)` mode. AlphaGSM can install the
generic Source SDK Base 2013 Dedicated Server scaffold from anonymous SteamCMD,
but it still needs the real SourceForts Classic full-version content tree from
the official ModDB files page.

## Quick Start

Create the server:

```bash
alphagsm mysfcserve create sfcserver
```

Run setup:

```bash
alphagsm mysfcserve setup
```

Start it:

```bash
alphagsm mysfcserve start
```

Check it:

```bash
alphagsm mysfcserve status
```

Stop it:

```bash
alphagsm mysfcserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the executable name
- SteamCMD downloads the server files
- default configuration and backup settings

Before `start`, download the latest SourceForts Classic full-version archive
from the official ModDB files page and extract the resulting `sfclassic/` tree
so `<install_dir>/sfclassic/maps/sf_astrodome.bsp` exists. If `setup` or
`start` reports an `ENABLED (BYO)` requirement, the public app `244310` payload
alone is still not enough for this module.

## Useful Commands

```bash
alphagsm mysfcserve update
alphagsm mysfcserve backup
```

## Notes

- Module name: `sfcserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `244310`
- **SteamCMD App Name**: `Source SDK Base 2013 Dedicated Server`

### Server Configuration

- **Config file**: `sfclassic/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `sf_astrodome`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/sfcserver/](../server-templates/sfcserver/)

### Maps and Mods

- **Map directory**: `sfclassic/maps/`
- **Mod directory**: `sfclassic/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/sfclassic/`.
- **Current status**: Supported in `ENABLED (BYO)` mode. Anonymous SteamCMD app `244310` still only provides the generic SDK scaffold, so stage the real `sfclassic/` content tree from the official SourceForts Classic ModDB full-version archive before retrying startup.
- **Map install**: Copy `.bsp` files into `sfclassic/maps/` and add to `sfclassic/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `sfclassic/addons/`.
