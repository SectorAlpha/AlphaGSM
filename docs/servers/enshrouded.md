# Enshrouded

This guide covers the `enshrouded` module in AlphaGSM.

`enshrouded` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The validated Linux path is Docker-backed through the shared
`wine-proton` runtime.

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
- the query port in `enshrouded_server.json` (default 15637)
- the server name in `enshrouded_server.json`
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
- Default query port: `15637`

## Developer Notes

### Run File

- **Executable**: `enshrouded_server.exe`
- **Location**: `<install_dir>/enshrouded_server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2278520`

### Server Configuration

- **Config file**: `enshrouded_server.json`
- **Managed keys**: `queryport`, `servername`
- **Notes**: `enshrouded_server.json` is authoritative for `queryPort` and
  `name`. AlphaGSM preserves unrelated generated settings and still supplies
  the save-name launch argument.
- **Template**: See [server-templates/enshrouded/](../server-templates/enshrouded/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
