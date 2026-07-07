# Assetto Corsa Competizione

This guide covers the `accserver` module in AlphaGSM.

## Status

`accserver` is currently `ENABLED (AUTH)` on the documented Ubuntu 24.04
Linux baseline.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Assetto Corsa Competizione dedicated server app `1430110`. The current GitHub
integration lane still validates both process and Docker runtime selection
around that auth-gated prerequisite, while local runs remain process-backed by
default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaccserve create accserver
```

Run setup:

```bash
alphagsm myaccserve setup
```

Start it:

```bash
alphagsm myaccserve start
```

Check it:

```bash
alphagsm myaccserve status
```

Stop it:

```bash
alphagsm myaccserve stop
```

## Setup Details

Setup configures:

- the game port (default 9231)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myaccserve update
alphagsm myaccserve backup
```

## Notes

- Module name: `accserver`
- Default port: 9231

## Developer Notes

### Run File

- **Executable**: `server/accServer.exe`
- **Location**: `<install_dir>/server/accServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1430110`

### Server Configuration

- **Config file**: `configuration.json`
- **Template**: See [server-templates/accserver/](../server-templates/accserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
