# Project CARS 2

This guide covers the `pcars2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypcars2se create pcars2server
```

Run setup:

```bash
alphagsm mypcars2se setup
```

Start it:

```bash
alphagsm mypcars2se start
```

Check it:

```bash
alphagsm mypcars2se status
```

Stop it:

```bash
alphagsm mypcars2se stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypcars2se update
alphagsm mypcars2se backup
```

## Notes

- Module name: `pcars2server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `DedicatedServerCmd`
- **Location**: `<install_dir>/DedicatedServerCmd`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `413770`

### Server Configuration

- **Config file**: `server.cfg`
- **Template**: See [server-templates/pcars2server/](../server-templates/pcars2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
