# Pavlov VR

This guide covers the `pvrserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mypvrserve create pvrserver
```

Run setup:

```bash
alphagsm mypvrserve setup
```

Start it:

```bash
alphagsm mypvrserve start
```

Check it:

```bash
alphagsm mypvrserve status
```

Stop it:

```bash
alphagsm mypvrserve stop
```

## Setup Details

Setup configures:

- the game port (default 9100)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mypvrserve update
alphagsm mypvrserve backup
```

## Notes

- Module name: `pvrserver`
- Default port: 9100

## Developer Notes

### Run File

- **Executable**: `PavlovServer.sh`
- **Location**: `<install_dir>/PavlovServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `622970`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/pvrserver/](../server-templates/pvrserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
