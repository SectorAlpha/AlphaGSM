# Sunkenland

This guide covers the `sunkenlandserver` module in AlphaGSM.

`sunkenlandserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysunkenla create sunkenlandserver
```

Run setup:

```bash
alphagsm mysunkenla setup
```

Start it:

```bash
alphagsm mysunkenla start
```

Check it:

```bash
alphagsm mysunkenla status
```

Stop it:

```bash
alphagsm mysunkenla stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysunkenla update
alphagsm mysunkenla backup
```

## Notes

- Module name: `sunkenlandserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Sunkenland-DedicatedServer.exe`
- **Location**: `<install_dir>/Sunkenland-DedicatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2667530`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/sunkenlandserver/](../server-templates/sunkenlandserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
