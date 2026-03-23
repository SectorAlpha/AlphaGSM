# Sniper Elite 4

This guide covers the `sniperelite4server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysniperel create sniperelite4server
```

Run setup:

```bash
alphagsm mysniperel setup
```

Start it:

```bash
alphagsm mysniperel start
```

Check it:

```bash
alphagsm mysniperel status
```

Stop it:

```bash
alphagsm mysniperel stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysniperel update
alphagsm mysniperel backup
```

## Notes

- Module name: `sniperelite4server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `SniperElite4_DedicatedServer.exe`
- **Location**: `<install_dir>/SniperElite4_DedicatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `568880`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `12`
- **Template**: See [server-templates/sniperelite4server/](../server-templates/sniperelite4server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
