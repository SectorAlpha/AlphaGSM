# Enshrouded

This guide covers the `enshrouded` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myenshroud create enshrouded
```

Run setup:

```bash
alphagsm myenshroud setup
```

Start it:

```bash
alphagsm myenshroud start
```

Check it:

```bash
alphagsm myenshroud status
```

Stop it:

```bash
alphagsm myenshroud stop
```

## Setup Details

Setup configures:

- the game port (default 15637)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myenshroud update
alphagsm myenshroud backup
```

## Notes

- Module name: `enshrouded`
- Default game port: `15637`
- Default query port: `15638`

## Developer Notes

### Run File

- **Executable**: `enshrouded_server.exe`
- **Location**: `<install_dir>/enshrouded_server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2278520`

### Server Configuration

- **Config file**: `enshrouded_server.json`
- **Notes**: `queryPort` and the JSON settings live in `enshrouded_server.json`; AlphaGSM still supplies the separate game port and save-name via launch arguments
- **Template**: See [server-templates/enshrouded/](../server-templates/enshrouded/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
