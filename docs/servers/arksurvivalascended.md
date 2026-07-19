# ARK: Survival Ascended

This guide covers the `arksurvivalascended` module in AlphaGSM.

`arksurvivalascended` retains its prior `PASSED` status from 2026-05-30 on the
documented Ubuntu 24.04 Linux baseline. The current runtime/protocol correction
is pending replacement GitHub validation and does not record a new pass. The
checked-in Linux validation path is Docker-backed through the module's
`wine-proton` runtime contract.

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

- the game port (default `7777`)
- a distinct A2S query port (default `27015`)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myarksurvi update
alphagsm myarksurvi backup
```

## Notes

- Module name: `arksurvivalascended`
- Default game port: `7777`
- Default query port: `27015`
- `query`, `info`, and `info --json` resolve the selected runtime host and use
  exact A2S on the managed query port
- The runtime claims and publishes game UDP, `game + 1` UDP, and query UDP
- Current correction status: replacement GitHub validation pending

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Win64/ArkAscendedServer.exe`
- **Location**: `<install_dir>/ShooterGame/Binaries/Win64/ArkAscendedServer.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2430930`

The documented Linux path runs through AlphaGSM's Docker-backed
`wine-proton` runtime image rather than a host `screen` session. Anonymous
SteamCMD setup for app `2430930` succeeds on the current branch. The module
delegates Docker launch to the shared Proton runtime builder, then queries the
runtime-resolved host through A2S on the distinct managed query port.

The launch keeps the map as the leading travel value, passes the game port as
`-port=<game>`, and leaves `Port` out of the map URL. When configured,
`ServerPassword` appears before the final `ServerAdminPassword`. The runtime
publishes the game port and its adjacent UDP port as well as the distinct UDP
query port.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/arksurvivalascended/](../server-templates/arksurvivalascended/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
