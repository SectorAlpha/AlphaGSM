# Project Zomboid

This guide covers the `projectzomboid` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprojectz create projectzomboid
```

Run setup:

```bash
alphagsm myprojectz setup
```

Start it:

```bash
alphagsm myprojectz start
```

Check it:

```bash
alphagsm myprojectz status
```

Stop it:

```bash
alphagsm myprojectz stop
```

## Setup Details

Setup configures:

- the game port (default 16261)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myprojectz update
alphagsm myprojectz backup
```

## Notes

- Module name: `projectzomboid`
- Default port: 16261

## Developer Notes

### Run File

- **Executable**: `start-server.sh`
- **Location**: `<install_dir>/start-server.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `380870`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/projectzomboid/](../server-templates/projectzomboid/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
