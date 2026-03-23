# Valheim

This guide covers the `valheim` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myvalheim create valheim
```

Run setup:

```bash
alphagsm myvalheim setup
```

Start it:

```bash
alphagsm myvalheim start
```

Check it:

```bash
alphagsm myvalheim status
```

Stop it:

```bash
alphagsm myvalheim stop
```

## Setup Details

Setup configures:

- the game port (default 2456)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myvalheim update
alphagsm myvalheim backup
```

## Notes

- Module name: `valheim`
- Default port: 2456

## Developer Notes

### Run File

- **Executable**: `valheim_server.x86_64`
- **Location**: `<install_dir>/valheim_server.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `896660`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/valheim/](../server-templates/valheim/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
