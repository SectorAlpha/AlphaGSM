# ASTRONEER

This guide covers the `astroneerserver` module in AlphaGSM.

## Requirements

- Docker recommended on Linux: branch-local or published `alphagsm-wine-proton-runtime`
- Host/process fallback: `screen` plus a working Wine/Proton install
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myastronee create astroneerserver
```

Run setup:

```bash
alphagsm myastronee setup
```

Start it:

```bash
alphagsm myastronee start
```

Check it:

```bash
alphagsm myastronee status
```

Stop it:

```bash
alphagsm myastronee stop
```

## Setup Details

Setup configures:

- the game port (default 8777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myastronee update
alphagsm myastronee backup
```

## Notes

- Module name: `astroneerserver`
- Default port: 8777
- Current supported validation lane: Docker runtime on Linux
- `query`, `info`, and `info --json` use a generic `tcp` probe on the main port

## Developer Notes

### Run File

- **Executable**: `AstroServer.exe`
- **Location**: `<install_dir>/AstroServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `728470`
- **Docker runtime note**: the shared `wine-proton` entrypoint now starts Xvfb for this module so the bundled UE4 prerequisite bootstrap can complete instead of aborting on `Failed to create window`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/astroneerserver/](../server-templates/astroneerserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
