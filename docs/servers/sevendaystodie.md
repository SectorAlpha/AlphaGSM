# 7 Days to Die

This guide covers the `sevendaystodie` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysevenday create sevendaystodie
```

Run setup:

```bash
alphagsm mysevenday setup
```

Start it:

```bash
alphagsm mysevenday start
```

Check it:

```bash
alphagsm mysevenday status
```

Stop it:

```bash
alphagsm mysevenday stop
```

## Setup Details

Setup configures:

- the game port (default 26900)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysevenday update
alphagsm mysevenday backup
```

## Notes

- Module name: `sevendaystodie`
- Default port: 26900

## Developer Notes

### Run File

- **Executable**: `startserver.sh`
- **Location**: `<install_dir>/startserver.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `294420`

### Server Configuration

- **Config file**: `serverconfig.xml`
- **Template**: See [server-templates/sevendaystodie/](../server-templates/sevendaystodie/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
