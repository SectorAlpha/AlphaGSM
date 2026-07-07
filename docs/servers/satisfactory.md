# Satisfactory

This guide covers the `satisfactory` module in AlphaGSM.

`satisfactory` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysatisfac create satisfactory
```

Run setup:

```bash
alphagsm mysatisfac setup
```

Start it:

```bash
alphagsm mysatisfac start
```

Check it:

```bash
alphagsm mysatisfac status
```

Stop it:

```bash
alphagsm mysatisfac stop
```

## Setup Details

Setup configures:

- the game port (default 15777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysatisfac update
alphagsm mysatisfac backup
```

## Notes

- Module name: `satisfactory`
- Default port: 15777

## Developer Notes

### Run File

- **Executable**: `FactoryServer.sh`
- **Location**: `<install_dir>/FactoryServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1690800`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/satisfactory/](../server-templates/satisfactory/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
