# Day of Dragons

This guide covers the `dayofdragonsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mydayofdra create dayofdragonsserver
```

Run setup:

```bash
alphagsm mydayofdra setup
```

Start it:

```bash
alphagsm mydayofdra start
```

Check it:

```bash
alphagsm mydayofdra status
```

Stop it:

```bash
alphagsm mydayofdra stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mydayofdra update
alphagsm mydayofdra backup
```

## Notes

- Module name: `dayofdragonsserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `DragonsServer.sh`
- **Location**: `<install_dir>/DragonsServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1088320`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/dayofdragonsserver/](../server-templates/dayofdragonsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
