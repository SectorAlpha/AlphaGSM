# DayZ

This guide covers the `dayzserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayzserv create dayzserver
```

Run setup:

```bash
alphagsm mydayzserv setup
```

Start it:

```bash
alphagsm mydayzserv start
```

Check it:

```bash
alphagsm mydayzserv status
```

Stop it:

```bash
alphagsm mydayzserv stop
```

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayzserv update
alphagsm mydayzserv backup
alphagsm mydayzserv set servername "AlphaGSM DayZ"
alphagsm mydayzserv set queryport 2303
```

`set servername`, `set serverpassword`, `set adminpassword`, `set maxplayers`, and `set queryport` rewrite `serverDZ.cfg` immediately through the schema-backed config-sync path.

## Notes

- Module name: `dayzserver`
- Default port: 2302

## Developer Notes

### Run File

- **Executable**: `DayZServer`
- **Location**: `<install_dir>/DayZServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `223350`

### Server Configuration

- **Config file**: `serverDZ.cfg`
- **Template**: See [server-templates/dayzserver/](../server-templates/dayzserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `hostname`, `password`, `passwordAdmin`, `maxPlayers`, and `steamQueryPort` aligned with `set`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
