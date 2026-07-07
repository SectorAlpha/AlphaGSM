# Brickadia

This guide covers the `brickadiaserver` module in AlphaGSM.

## Status

`brickadiaserver` is currently `ENABLED (AUTH)` on the documented Ubuntu 24.04
Linux baseline.

Before `setup`, authenticate Steam or SteamCMD with an account entitled to
Brickadia dedicated server app `3017590`. The current GitHub integration lane
still validates both process and Docker runtime selection around that
auth-gated prerequisite, while local runs remain process-backed by default
unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybrickadi create brickadiaserver
```

Run setup:

```bash
alphagsm mybrickadi setup
```

Start it:

```bash
alphagsm mybrickadi start
```

Check it:

```bash
alphagsm mybrickadi status
```

Stop it:

```bash
alphagsm mybrickadi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybrickadi update
alphagsm mybrickadi backup
```

## Notes

- Module name: `brickadiaserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `BrickadiaServer.sh`
- **Location**: `<install_dir>/BrickadiaServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3017590`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/brickadiaserver/](../server-templates/brickadiaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
