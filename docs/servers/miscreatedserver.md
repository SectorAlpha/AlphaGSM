# Miscreated

This guide covers the `miscreatedserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymiscreat create miscreatedserver
```

Run setup:

```bash
alphagsm mymiscreat setup
```

Start it:

```bash
alphagsm mymiscreat start
```

Check it:

```bash
alphagsm mymiscreat status
```

Stop it:

```bash
alphagsm mymiscreat stop
```

## Setup Details

Setup configures:

- the game port (default 64090)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymiscreat update
alphagsm mymiscreat backup
```

## Notes

- Module name: `miscreatedserver`
- Default port: 64090

## Developer Notes

### Run File

- **Executable**: `Bin64_dedicated/MiscreatedServer.exe`
- **Location**: `<install_dir>/Bin64_dedicated/MiscreatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `302200`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `50`
- **Template**: See [server-templates/miscreatedserver/](../server-templates/miscreatedserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
