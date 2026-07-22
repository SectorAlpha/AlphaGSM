# Reign Of Dwarf

This guide covers the `reignofdwarfserver` module in AlphaGSM.

`reignofdwarfserver` is currently `PASSED` on the documented Ubuntu 24.04
Linux baseline. GitHub keeps one Docker-default `wine-proton` lifecycle because
the forced host-Proton process exited before readiness.

## Requirements

- Docker
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myreignofd create reignofdwarfserver
```

Run setup:

```bash
alphagsm myreignofd setup
```

Start it:

```bash
alphagsm myreignofd start
```

Check it:

```bash
alphagsm myreignofd status
```

Stop it:

```bash
alphagsm myreignofd stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the Steam query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myreignofd update
alphagsm myreignofd backup
```

## Notes

- Module name: `reignofdwarfserver`
- Default game port: 7777
- Default Steam query port: 27015
- AlphaGSM supplies Unity's `-batchmode -nographics` launch flags so the
  dedicated payload does not require a graphical window in either runtime.
- Integration readiness uses AlphaGSM `info --json` protocol `a2s` rather than
  a host `screen` log.

## Developer Notes

### Run File

- **Executable**: `Server.exe`
- **Location**: `<install_dir>/Server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1999160`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `16`
- **Template**: See [server-templates/reignofdwarfserver/](../server-templates/reignofdwarfserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
