# Interstellar Rift

This guide covers the `interstellarriftserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myinterste create interstellarriftserver
```

Run setup:

```bash
alphagsm myinterste setup
```

Start it:

```bash
alphagsm myinterste start
```

Check it:

```bash
alphagsm myinterste status
```

Stop it:

```bash
alphagsm myinterste stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myinterste update
alphagsm myinterste backup
```

## Notes

- Module name: `interstellarriftserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `InterstellarRiftServer.x86_64`
- **Location**: `<install_dir>/InterstellarRiftServer.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `363360`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/interstellarriftserver/](../server-templates/interstellarriftserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
