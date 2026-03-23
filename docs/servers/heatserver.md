# Heat

This guide covers the `heatserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myheatserv create heatserver
```

Run setup:

```bash
alphagsm myheatserv setup
```

Start it:

```bash
alphagsm myheatserv start
```

Check it:

```bash
alphagsm myheatserv status
```

Stop it:

```bash
alphagsm myheatserv stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myheatserv update
alphagsm myheatserv backup
```

## Notes

- Module name: `heatserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `HeatServer.exe`
- **Location**: `<install_dir>/HeatServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `996600`

### Server Configuration

- **Config files**: `ServerConfig.cfg`
- **Max players**: `32`
- **Template**: See [server-templates/heatserver/](../server-templates/heatserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
