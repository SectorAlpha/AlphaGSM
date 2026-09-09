# Night of the Dead

This guide covers the `notdserver` module in AlphaGSM.

Status: PASSED on 2026-05-29

## Requirements

- Docker recommended on Linux: branch-local or published `alphagsm-wine-proton-runtime`
- Host/process fallback: `screen` plus a working Wine/Proton install
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynotdserv create notdserver
```

Run setup:

```bash
alphagsm mynotdserv setup
```

Start it:

```bash
alphagsm mynotdserv start
```

Check it:

```bash
alphagsm mynotdserv status
```

Stop it:

```bash
alphagsm mynotdserv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated-server files
- AlphaGSM mirrors the root `ServerSettings.ini` into `LF/Saved/Config/ServerSettings.ini`
  before launch on Linux so the live runtime reads the managed settings

## Useful Commands

```bash
alphagsm mynotdserv update
alphagsm mynotdserv backup
```

## Notes

- Module name: `notdserver`
- Default port: `7777`
- Default query port: `27015`
- Current supported validation lane on Linux: Docker-backed `wine-proton`
- On Linux Wine/Proton, `query`, `info`, and `info --json` use the validated TCP
  listener on the managed game port; native Windows keeps A2S on `queryport`.

## Developer Notes

### Run File

- **Executable**: `LFServer.exe`
- **Location**: `<install_dir>/LFServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1420710`

### Server Configuration

- **Config files**: root `ServerSettings.ini`, mirrored at `LF/Saved/Config/ServerSettings.ini`
- **Template**: See [server-templates/notdserver/](../server-templates/notdserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
