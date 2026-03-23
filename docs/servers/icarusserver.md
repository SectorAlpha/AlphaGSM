# Icarus

This guide covers the `icarusserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myicarusse create icarusserver
```

Run setup:

```bash
alphagsm myicarusse setup
```

Start it:

```bash
alphagsm myicarusse start
```

Check it:

```bash
alphagsm myicarusse status
```

Stop it:

```bash
alphagsm myicarusse stop
```

## Setup Details

Setup configures:

- the game port (default 17778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myicarusse update
alphagsm myicarusse backup
```

## Notes

- Module name: `icarusserver`
- Default port: 17778

## Developer Notes

### Run File

- **Executable**: `IcarusServer.exe`
- **Location**: `<install_dir>/IcarusServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2089300`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/icarusserver/](../server-templates/icarusserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
