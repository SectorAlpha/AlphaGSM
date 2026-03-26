# Palworld

This guide covers the `palworld` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypalworld create palworld
```

Run setup:

```bash
alphagsm mypalworld setup
```

Start it:

```bash
alphagsm mypalworld start
```

Check it:

```bash
alphagsm mypalworld status
```

Stop it:

```bash
alphagsm mypalworld stop
```

## Setup Details

Setup configures:

- the game port (default 8211)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypalworld update
alphagsm mypalworld backup
```

## Notes

- Module name: `palworld`
- Default port: 8211

## Developer Notes

### Run File

- **Executable**: `PalServer.sh`
- **Location**: `<install_dir>/PalServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2394010`

### Server Configuration

- **Config files**: `DefaultPalWorldSettings.ini`, `PalWorldSettings.ini`
- **Template**: See [server-templates/palworld/](../server-templates/palworld/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
