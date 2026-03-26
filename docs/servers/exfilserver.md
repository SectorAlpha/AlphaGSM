# Exfil

This guide covers the `exfilserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myexfilser create exfilserver
```

Run setup:

```bash
alphagsm myexfilser setup
```

Start it:

```bash
alphagsm myexfilser start
```

Check it:

```bash
alphagsm myexfilser status
```

Stop it:

```bash
alphagsm myexfilser stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myexfilser update
alphagsm myexfilser backup
```

## Notes

- Module name: `exfilserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `ExfilServer.sh`
- **Location**: `<install_dir>/ExfilServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3093190`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/exfilserver/](../server-templates/exfilserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
