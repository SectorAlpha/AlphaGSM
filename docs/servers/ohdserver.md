# Operation: Harsh Doorstop

This guide covers the `ohdserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myohdserve create ohdserver
```

Run setup:

```bash
alphagsm myohdserve setup
```

Start it:

```bash
alphagsm myohdserve start
```

Check it:

```bash
alphagsm myohdserve status
```

Stop it:

```bash
alphagsm myohdserve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myohdserve update
alphagsm myohdserve backup
```

## Notes

- Module name: `ohdserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `OHDServer.sh`
- **Location**: `<install_dir>/OHDServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `950900`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/ohdserver/](../server-templates/ohdserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
