# The Forest

This guide covers the `theforestserver` module in AlphaGSM.

`theforestserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mythefores create theforestserver
```

Run setup:

```bash
alphagsm mythefores setup
```

Start it:

```bash
alphagsm mythefores start
```

Check it:

```bash
alphagsm mythefores status
```

Stop it:

```bash
alphagsm mythefores stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mythefores update
alphagsm mythefores backup
```

## Notes

- Module name: `theforestserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `TheForestDedicatedServer.exe`
- **Location**: `<install_dir>/TheForestDedicatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `556450`

### Server Configuration

- **Config files**: `Server.cfg`
- **Template**: See [server-templates/theforestserver/](../server-templates/theforestserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
