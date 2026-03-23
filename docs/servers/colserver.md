# Colony Survival

This guide covers the `colserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycolserve create colserver
```

Run setup:

```bash
alphagsm mycolserve setup
```

Start it:

```bash
alphagsm mycolserve start
```

Check it:

```bash
alphagsm mycolserve status
```

Stop it:

```bash
alphagsm mycolserve stop
```

## Setup Details

Setup configures:

- the game port (default 27004)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mycolserve update
alphagsm mycolserve backup
```

## Notes

- Module name: `colserver`
- Default port: 27004

## Developer Notes

### Run File

- **Executable**: `ColonyServer.x86_64`
- **Location**: `<install_dir>/ColonyServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `748090`

### Server Configuration

- **Config files**: `server_settings.json`
- **Max players**: `16`
- **Template**: See [server-templates/colserver/](../server-templates/colserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
