# American Truck Simulator

This guide covers the `atsserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myatsserve create atsserver
```

Run setup:

```bash
alphagsm myatsserve setup
```

Start it:

```bash
alphagsm myatsserve start
```

Check it:

```bash
alphagsm myatsserve status
```

Stop it:

```bash
alphagsm myatsserve stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myatsserve update
alphagsm myatsserve backup
```

## Notes

- Module name: `atsserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `bin/linux_x64/americantruck_server`
- **Location**: `<install_dir>/bin/linux_x64/americantruck_server`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2239530`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/atsserver/](../server-templates/atsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
