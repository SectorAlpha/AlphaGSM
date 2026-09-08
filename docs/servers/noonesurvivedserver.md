# No One Survived

This guide covers the `noonesurvivedserver` module in AlphaGSM.

Status: PASSED on 2026-05-29

## Requirements

- Docker recommended on Linux: branch-local or published `alphagsm-wine-proton-runtime`
- Host/process fallback: `screen` plus a working Wine/Proton install
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynoonesur create noonesurvivedserver
```

Run setup:

```bash
alphagsm mynoonesur setup
```

Start it:

```bash
alphagsm mynoonesur start
```

Check it:

```bash
alphagsm mynoonesur status
```

Stop it:

```bash
alphagsm mynoonesur stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated-server files

## Useful Commands

```bash
alphagsm mynoonesur update
alphagsm mynoonesur backup
```

## Notes

- Module name: `noonesurvivedserver`
- Default port: `7777`
- Default query port: `27015`
- Current supported validation lane on Linux: Docker-backed `wine-proton`
- `query`, `info`, and `info --json` use native Steam A2S on `queryport`,
  including Linux Wine/Proton launches.

## Developer Notes

### Run File

- **Executable**: `WRSHServer.exe`
- **Location**: `<install_dir>/WRSHServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2329680`

### Server Configuration

- **Config file**: launch settings are passed directly on the command line from the managed datastore
- **Template**: See [server-templates/noonesurvivedserver/](../server-templates/noonesurvivedserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
