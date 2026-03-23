# BATTALION: Legacy

This guide covers the `btlserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybtlserve create btlserver
```

Run setup:

```bash
alphagsm mybtlserve setup
```

Start it:

```bash
alphagsm mybtlserve start
```

Check it:

```bash
alphagsm mybtlserve status
```

Stop it:

```bash
alphagsm mybtlserve stop
```

## Setup Details

Setup configures:

- the game port (default 7788)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybtlserve update
alphagsm mybtlserve backup
```

## Notes

- Module name: `btlserver`
- Default port: 7788

## Developer Notes

### Run File

- **Executable**: `Battalion/Binaries/Linux/BattalionServer-Linux-Shipping`
- **Location**: `<install_dir>/Battalion/Binaries/Linux/BattalionServer-Linux-Shipping`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `805140`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/btlserver/](../server-templates/btlserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
