# Argo

This guide covers the `argoserver` module in AlphaGSM.

## Support Status

`argoserver` is supported on Linux.

The validated path is:

- anonymous SteamCMD install from app `563930` on its public branch
- the shared Docker-backed `steamcmd-linux` runtime
- the real native binary `argoserver`

AlphaGSM manages the native `server.cfg`, lifecycle, and current generic `tcp`
health surface on the managed main game port.

## Quick Start

Create the server:

```bash
alphagsm myargoserv create argoserver
```

Run setup:

```bash
alphagsm myargoserv setup
```

Start it:

```bash
alphagsm myargoserv start
```

Check it:

```bash
alphagsm myargoserv status
```

Stop it:

```bash
alphagsm myargoserv stop
```

## Requirements

- Docker for the validated Linux runtime path
- SteamCMD
- Python packages from `requirements.txt`

## Setup Details

Setup configures:

- the game port (default 2302)
- the install directory
- SteamCMD downloads the server files anonymously from app `563930`
- AlphaGSM writes `server.cfg`

## Useful Commands

```bash
alphagsm myargoserv update
alphagsm myargoserv backup
```

## Notes

- Module name: `argoserver`
- Default port: 2302
- Default executable: `argoserver`
- Default world: `empty`

## Developer Notes

### Run File

- **Executable**: `argoserver`
- **Location**: `<install_dir>/argoserver`
- **Engine**: Arma/Bohemia native Linux dedicated server
- **SteamCMD App ID**: `563930`
- **SteamCMD branch**: public/default

### Server Configuration

- **Config file**: `server.cfg`
- **Managed key**: `servername` syncs to `hostname`
- **Template**: See [server-templates/argoserver/](../server-templates/argoserver/) if available

### Runtime Notes

- The old disabled note was stale: the anonymous payload does include a native Linux server.
- AlphaGSM does not force the removed `server` beta; current SteamCMD rejects
  that branch, while the public branch is the last validated install path.
- The validated health contract is generic `tcp` on the managed main game port rather than A2S.
- The validated Linux path is the shared Docker-backed `steamcmd-linux` runtime.
