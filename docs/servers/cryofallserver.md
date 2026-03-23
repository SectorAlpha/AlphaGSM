# CryoFall

This guide covers the `cryofallserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycryofall create cryofallserver
```

Run setup:

```bash
alphagsm mycryofall setup
```

Start it:

```bash
alphagsm mycryofall start
```

Check it:

```bash
alphagsm mycryofall status
```

Stop it:

```bash
alphagsm mycryofall stop
```

## Setup Details

Setup configures:

- the game port (default 49001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycryofall update
alphagsm mycryofall backup
```

## Notes

- Module name: `cryofallserver`
- Default port: 49001

## Developer Notes

### Run File

- **Executable**: `CryoFall_Server`
- **Location**: `<install_dir>/CryoFall_Server`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1061710`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/cryofallserver/](../server-templates/cryofallserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
