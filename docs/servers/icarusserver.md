# Icarus

This guide covers the `icarusserver` module in AlphaGSM.

## Requirements

- Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myicarusse create icarusserver
```

Run setup:

```bash
alphagsm myicarusse setup
```

Start it:

```bash
alphagsm myicarusse start
```

Check it:

```bash
alphagsm myicarusse status
```

Stop it:

```bash
alphagsm myicarusse stop
```

## Setup Details

Setup configures:

- the game port (default 17778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myicarusse update
alphagsm myicarusse backup
```

## Notes

- Module name: `icarusserver`
- Default port: 17778
- Current validation status: PASSED 2026-05-30. Fresh smoke and integration
  now both pass on the Docker-backed Linux `wine-proton` runtime once
  AlphaGSM uses the shared in-container Xvfb/software-GL path and treats
  Icarus' live health surface honestly: `query`, `info`, and `info --json`
  answer as generic `tcp` on the managed main game port instead of the older
  stale log-marker and A2S assumptions.

## Developer Notes

### Run File

- **Executable**: `IcarusServer.exe`
- **Location**: `<install_dir>/IcarusServer.exe`
- **Engine**: Windows dedicated server via Wine/Proton
- **SteamCMD App ID**: `2089300`

The validated Linux path now runs through AlphaGSM's Docker-backed
`wine-proton` runtime image rather than a host `screen` session. Anonymous
SteamCMD setup for app `2089300` succeeds on the current branch, and the live
server answers `query`, `info`, and `info --json` as generic `tcp` on the
managed main port. The older `Saved/Logs/Icarus.log` readiness assumption and
the stale A2S-style info contract are no longer part of the supported Linux
path.

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/icarusserver/](../server-templates/icarusserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
