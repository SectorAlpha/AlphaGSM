# ARK: Survival Ascended

This guide covers the `arksurvivalascended` module in AlphaGSM.

`arksurvivalascended` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The checked-in GitHub validation path for this server is Docker-backed, so the documented Linux lifecycle is proven through the module's container runtime contract first.

## Requirements

- Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myarksurvi create arksurvivalascended
```

Run setup:

```bash
alphagsm myarksurvi setup
```

Start it:

```bash
alphagsm myarksurvi start
```

Check it:

```bash
alphagsm myarksurvi status
```

Stop it:

```bash
alphagsm myarksurvi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarksurvi update
alphagsm myarksurvi backup
```

## Notes

- Module name: `arksurvivalascended`
- Default port: 27015
- Current validation status: PASSED 2026-05-30. Fresh smoke and integration
  now both pass on the Docker-backed Linux `wine-proton` runtime with
  anonymous SteamCMD install for app `2430930`, and the supported Linux
  health surface is generic `tcp` on the managed main game port instead of
  the older stale log-marker and A2S assumptions.

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Win64/ArkAscendedServer.exe`
- **Location**: `<install_dir>/ShooterGame/Binaries/Win64/ArkAscendedServer.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2430930`

The validated Linux path now runs through AlphaGSM's Docker-backed
`wine-proton` runtime image rather than a host `screen` session. Anonymous
SteamCMD setup for app `2430930` succeeds on the current branch, and the live
server answers `query`, `info`, and `info --json` as generic `tcp` on the
managed main port. The older `ShooterGame.log` readiness marker and A2S-style
info assumptions are no longer part of the supported Linux path. The module
delegates its Docker launch to the shared Proton runtime builder, so the
container entrypoint runs `ArkAscendedServer.exe` through Proton rather than
executing the Windows binary directly.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/arksurvivalascended/](../server-templates/arksurvivalascended/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
