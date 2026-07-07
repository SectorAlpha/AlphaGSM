# Squad

This guide covers the `squadserver` module in AlphaGSM.

`squadserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysquadser create squadserver
```

Run setup:

```bash
alphagsm mysquadser setup
```

Start it:

```bash
alphagsm mysquadser start
```

Check it:

```bash
alphagsm mysquadser status
```

Stop it:

```bash
alphagsm mysquadser stop
```

## Setup Details

Setup configures:

- the game port (default 27165)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysquadser update
alphagsm mysquadser backup
```

## Notes

- Module name: `squadserver`
- Default port: 27165

## Developer Notes

### Run File

- **Executable**: `SquadGameServer.sh`
- **Location**: `<install_dir>/SquadGameServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `403240`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/squadserver/](../server-templates/squadserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
