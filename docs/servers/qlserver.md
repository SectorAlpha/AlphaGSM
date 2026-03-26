# Quake Live

This guide covers the `qlserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myqlserver create qlserver
```

Run setup:

```bash
alphagsm myqlserver setup
```

Start it:

```bash
alphagsm myqlserver start
```

Check it:

```bash
alphagsm myqlserver status
```

Stop it:

```bash
alphagsm myqlserver stop
```

## Setup Details

Setup configures:

- the game port (default 27960)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myqlserver update
alphagsm myqlserver backup
```

## Notes

- Module name: `qlserver`
- Default port: 27960

## Developer Notes

### Run File

- **Executable**: `qzeroded.x64`
- **Location**: `<install_dir>/qzeroded.x64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `349090`

### Server Configuration

- **Config files**: `baseq3/server.cfg`
- **Template**: See [server-templates/qlserver/](../server-templates/qlserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
