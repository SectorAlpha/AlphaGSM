# Remnants

This guide covers the `remnantsserver` module in AlphaGSM.

`remnantsserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. GitHub keeps one Docker-default `wine-proton` lifecycle because the
forced host-Proton process exited before readiness. The current payload exposes
generic TCP health on the configured game port rather than A2S on `queryport`.

## Requirements

- Docker
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myremnants create remnantsserver
```

Run setup:

```bash
alphagsm myremnants setup
```

Start it:

```bash
alphagsm myremnants start
```

Check it:

```bash
alphagsm myremnants status
```

Stop it:

```bash
alphagsm myremnants stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myremnants update
alphagsm myremnants backup
```

## Notes

- Module name: `remnantsserver`
- Default game port: 7777
- Default query port: 27015

## Developer Notes

### Run File

- **Executable**: `RemSurvivalServer.exe`
- **Location**: `<install_dir>/RemSurvivalServer.exe`
- **Engine**: UE4 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `1141420`

Integration validation polls AlphaGSM `info --json` protocol `a2s` directly,
so Docker readiness does not depend on an install-tree or host `screen` log.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/remnantsserver/](../server-templates/remnantsserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
