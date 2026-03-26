# GROUND BRANCH

This guide covers the `groundbranchserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygroundbr create groundbranchserver
```

Run setup:

```bash
alphagsm mygroundbr setup
```

Start it:

```bash
alphagsm mygroundbr start
```

Check it:

```bash
alphagsm mygroundbr status
```

Stop it:

```bash
alphagsm mygroundbr stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mygroundbr update
alphagsm mygroundbr backup
```

## Notes

- Module name: `groundbranchserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `GroundBranchServer-Win64-Shipping.exe`
- **Location**: `<install_dir>/GroundBranchServer-Win64-Shipping.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `476400`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `16`
- **Template**: See [server-templates/groundbranchserver/](../server-templates/groundbranchserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
