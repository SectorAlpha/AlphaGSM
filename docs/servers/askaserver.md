# ASKA

This guide covers the `askaserver` module in AlphaGSM.

`askaserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myaskaserv create askaserver
```

Run setup:

```bash
alphagsm myaskaserv setup
```

Start it:

```bash
alphagsm myaskaserv start
```

Check it:

```bash
alphagsm myaskaserv status
```

Stop it:

```bash
alphagsm myaskaserv stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myaskaserv update
alphagsm myaskaserv backup
```

## Notes

- Module name: `askaserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `AskaServer.exe`
- **Location**: `<install_dir>/AskaServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3246670`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `4`
- **Template**: See [server-templates/askaserver/](../server-templates/askaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
