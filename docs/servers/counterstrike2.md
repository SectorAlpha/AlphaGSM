# counterstrike2

This guide covers the `counterstrike2` module in AlphaGSM.

```bash
alphagsm myserver create counterstrike2
```

`cs2server` is an alias for this module.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycs2 create counterstrike2
```

Run setup:

```bash
alphagsm mycs2 setup
```

Start it:

```bash
alphagsm mycs2 start
```

Check it:

```bash
alphagsm mycs2 status
```

Stop it:

```bash
alphagsm mycs2 stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files for Steam app `730`
- the launcher defaults to `game/cs2.sh`
- Source config is written under `game/csgo/cfg/server.cfg`

## Notes

- Module name: `counterstrike2`
- Default port: 27015
- Current status: enabled in AlphaGSM integration and smoke surfaces.
- `counterstrikeglobaloffensive`, `csgo`, and `csgoserver` remain the legacy CS:GO surface backed by app `740`.

## Developer Notes

### Run File

- **Executable**: `game/cs2.sh`
- **Location**: `<install_dir>/game/cs2.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `730`

### Server Configuration

- **Config files**: `game/csgo/cfg/server.cfg`
- **Template**: Source game config scaffold created during install

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
