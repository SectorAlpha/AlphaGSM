# Survive the Nights

This guide covers the `stnserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystnserve create stnserver
```

Run setup:

```bash
alphagsm mystnserve setup
```

Start it:

```bash
alphagsm mystnserve start
```

Check it:

```bash
alphagsm mystnserve status
```

Stop it:

```bash
alphagsm mystnserve stop
```

## Setup Details

Setup configures:

- the game port (default 8888)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystnserve update
alphagsm mystnserve backup
alphagsm mystnserve set port 9999
```

`set port` rewrites `Config/ServerConfig.txt` immediately through the schema-backed config-sync path. The shared alias layer also accepts `gameport` for this module.

## Notes

- Module name: `stnserver`
- Default port: 8888

## Developer Notes

### Run File

- **Executable**: `Server_Linux_x64`
- **Location**: `<install_dir>/Server_Linux_x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1502300`

### Server Configuration

- **Config file**: `Config/ServerConfig.txt`
- **Template**: See [server-templates/stnserver/](../server-templates/stnserver/) if available
- **Schema-backed sync**: AlphaGSM keeps `Port=` aligned with `set port`

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
