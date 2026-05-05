# Project CARS

This guide covers the `pcarserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypcarserv create pcarserver
```

Run setup:

```bash
alphagsm mypcarserv setup
```

Start it:

```bash
alphagsm mypcarserv start
```

Check it:

```bash
alphagsm mypcarserv status
```

Stop it:

```bash
alphagsm mypcarserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypcarserv update
alphagsm mypcarserv backup
```

## Notes

- Module name: `pcarserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `DedicatedServerCmd`
- **Location**: `<install_dir>/DedicatedServerCmd`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `332670`

Smoke and integration validation track readiness through `alphagsm info --json`
returning protocol `a2s` instead of waiting for screen-log markers.

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/pcarserver/](../server-templates/pcarserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
