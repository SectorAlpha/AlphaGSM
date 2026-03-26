# ATLAS

This guide covers the `atlasserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myatlasser create atlasserver
```

Run setup:

```bash
alphagsm myatlasser setup
```

Start it:

```bash
alphagsm myatlasser start
```

Check it:

```bash
alphagsm myatlasser status
```

Stop it:

```bash
alphagsm myatlasser stop
```

## Setup Details

Setup configures:

- the game port (default 57561)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myatlasser update
alphagsm myatlasser backup
```

## Notes

- Module name: `atlasserver`
- Default port: 57561

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Linux/ShooterGameServer`
- **Location**: `<install_dir>/ShooterGame/Binaries/Linux/ShooterGameServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1006030`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/atlasserver/](../server-templates/atlasserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
