# Wurm Unlimited

This guide covers the `wurmserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mywurmserv create wurmserver
```

Run setup:

```bash
alphagsm mywurmserv setup
```

Start it:

```bash
alphagsm mywurmserv start
```

Check it:

```bash
alphagsm mywurmserv status
```

Stop it:

```bash
alphagsm mywurmserv stop
```

## Setup Details

Setup configures:

- the game port (default 3724)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mywurmserv update
alphagsm mywurmserv backup
```

## Notes

- Module name: `wurmserver`
- Default port: 3724

## Developer Notes

### Run File

- **Executable**: `WurmServerLauncher`
- **Location**: `<install_dir>/WurmServerLauncher`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `402370`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/wurmserver/](../server-templates/wurmserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
