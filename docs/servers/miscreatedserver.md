# Miscreated

This guide covers the `miscreatedserver` module in AlphaGSM.

Status: PASSED on 2026-05-29
The validated Ubuntu 24.04 path is one Docker-default `wine-proton` lifecycle;
CI does not duplicate an unproven host-Proton lane.

## Requirements

- Docker recommended on Linux: branch-local or published `alphagsm-wine-proton-runtime`
- Host/process fallback: `screen` plus a working Wine/Proton install
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymiscreat create miscreatedserver
```

Run setup:

```bash
alphagsm mymiscreat setup
```

Start it:

```bash
alphagsm mymiscreat start
```

Check it:

```bash
alphagsm mymiscreat status
```

Stop it:

```bash
alphagsm mymiscreat stop
```

## Setup Details

Setup configures:

- the game port (default 64090)
- the install directory
- SteamCMD downloads the Windows dedicated-server files
- readiness is tracked from `user/server.log` on the validated Linux Wine/Proton path

## Useful Commands

```bash
alphagsm mymiscreat update
alphagsm mymiscreat backup
```

## Notes

- Module name: `miscreatedserver`
- Default port: 64090
- Current supported validation lane on Linux: Docker-backed `wine-proton`
- On Linux, `query`, `info`, and `info --json` currently use generic `tcp`
  reachability on the managed game port instead of the older stale A2S probe
  on `port + 1`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create miscreatedserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `Bin64_dedicated/MiscreatedServer.exe`
- **Location**: `<install_dir>/Bin64_dedicated/MiscreatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `302200`

### Server Configuration

- **Config file**: launch settings are passed directly on the command line from the managed datastore
- **Max players**: `50`
- **Readiness log**: `user/server.log`
- **Template**: See [server-templates/miscreatedserver/](../server-templates/miscreatedserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
