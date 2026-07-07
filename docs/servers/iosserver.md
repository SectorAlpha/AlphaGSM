# IOSoccer

This guide covers the `iosserver` module in AlphaGSM.

`iosserver` is currently `ENABLED (AUTH)` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection around that provider-managed authentication prerequisite, while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myiosserve create iosserver
```

Run setup:

```bash
alphagsm myiosserve setup
```

Start it:

```bash
alphagsm myiosserve start
```

Check it:

```bash
alphagsm myiosserve status
```

Stop it:

```bash
alphagsm myiosserve stop
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
alphagsm myiosserve update
alphagsm myiosserve backup
```

## Notes

- Module name: `iosserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `srcds_run`
- **Location**: `<install_dir>/srcds_run`
- **Engine**: Source
- **SteamCMD App ID**: `673990`

Current validation status: `ENABLED (AUTH)`. AlphaGSM targets the dedicated
tool app `673990`, but the supported sdk2013 branches `iosoccer2025` / `beta`
are not anonymously accessible. Fresh SteamCMD probes against the dedicated
tool app still return `ERROR! Failed to set beta 'iosoccer2025'` for anonymous
login, while the public branch continues to crash on Linux after startup. The
supported path is authenticated Steam or SteamCMD access to the dedicated tool
branch before `setup`.

### Server Configuration

- **Config file**: `iosoccer/cfg/server.cfg`
- **Key settings**:
  - `hostname` — Server name
  - `sv_maxrate` — Max network rate
  - `rcon_password` — Remote console password
- **Default port**: `27015`
- **Default map**: `8v8_vienna`
- **Max players**: `32`
- **Ports**:
  - Game port: `27015` (UDP)
  - Client port: `27005` (UDP)
  - SourceTV port: `27020` (UDP)
- **Template**: See [server-templates/iosserver/](../server-templates/iosserver/)

### Maps and Mods

- **Map directory**: `iosoccer/maps/`
- **Mod directory**: `iosoccer/addons/`
- **Workshop support**: No
- **Mod notes**: AlphaGSM now supports `manifest`, direct archive `url`, `gamebanana`, and `moddb` addon sources for this server through the shared Source addon flow. The built-in manifest currently includes `metamod` and `sourcemod`. `mod cleanup` removes only AlphaGSM-tracked addon files and keeps cache/state under `.alphagsm/mods/iosoccer/`.
- **Map install**: Copy `.bsp` files into `iosoccer/maps/` and add to `iosoccer/cfg/mapcycle.txt`.
- **Mod install**: Copy addon folders into `iosoccer/addons/`.
