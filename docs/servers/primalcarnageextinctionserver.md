# Primal Carnage: Extinction

This guide covers the `primalcarnageextinctionserver` module in AlphaGSM.

`primalcarnageextinctionserver` is currently `PASSED` on the documented
Ubuntu 24.04 Linux baseline. The current GitHub integration lane still
exercises both process and Docker runtime selection, and the validated Linux
path remains Wine/Proton-backed with the corrected direct map-URL launch
contract feeding A2S `query` / `info` on the managed `queryport`.

## Requirements

- `screen` and `xvfb-run`
- Wine or Proton-GE on Linux hosts
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myprimalca create primalcarnageextinctionserver
```

Run setup:

```bash
alphagsm myprimalca setup
```

Start it:

```bash
alphagsm myprimalca start
```

Check it:

```bash
alphagsm myprimalca status
```

Stop it:

```bash
alphagsm myprimalca stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the A2S query port (default 27015)
- the install directory
- SteamCMD downloads the Windows dedicated server files

## Useful Commands

```bash
alphagsm myprimalca update
alphagsm myprimalca backup
```

## Notes

- Module name: `primalcarnageextinctionserver`
- Default game port: `7777`
- Default query port: `27015`

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/PrimalCarnageServer.exe`
- **Location**: `<install_dir>/Binaries/Win64/PrimalCarnageServer.exe`
- **Engine**: UE3 Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `336400`

Current validation status: the 2026-05-28 follow-up confirmed that
`PrimalCarnageServer.exe` must receive the map URL directly. Passing a literal
`SERVER` token makes UE3 try to load a missing package named `SERVER`, so
AlphaGSM now launches the dedicated binary as `PrimalCarnageServer.exe
PC-Docks?...?bIsDedicated=true -seekfreeloadingserver -log` and still wraps it
with `xvfb-run` on Linux. Focused validation also kept the claimed-port retry
path for the default `queryport` conflict on `27015`.
The process wrapper explicitly enables Wine's X11 driver inside that virtual
display, including when the parent environment disables it.

With the corrected argv, the server now writes `PrimalCarnageGame/Logs/Launch.log`,
loads `PC-Docks`, binds the UDP game/query ports, answers A2S on `queryport`,
and returns `info --json` with protocol `a2s`. The current bring-up markers to
watch before enforcing A2S are:

- `LoadMap: PC-Docks`
- `Game class is 'PCTeamDeathMatchGame'`
- `NetMode is now 1`

Focused validation also confirmed that `alphagsm stop` closes the live A2S
ports again. Update shared enablement trackers separately in the parent
integration change once the lane is cherry-picked.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/primalcarnageextinctionserver/](../server-templates/primalcarnageextinctionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
