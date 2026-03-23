# Staxel

This guide covers the `staxelserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystaxelse create staxelserver
```

Run setup:

```bash
alphagsm mystaxelse setup
```

Start it:

```bash
alphagsm mystaxelse start
```

Check it:

```bash
alphagsm mystaxelse status
```

Stop it:

```bash
alphagsm mystaxelse stop
```

## Setup Details

Setup configures:

- the game port (default 25565)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystaxelse update
alphagsm mystaxelse backup
```

## Notes

- Module name: `staxelserver`
- Default port: 25565

## Developer Notes

### Run File

- **Executable**: `bin/Staxel.ServerWizard.exe`
- **Location**: `<install_dir>/bin/Staxel.ServerWizard.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `755170`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/staxelserver/](../server-templates/staxelserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
