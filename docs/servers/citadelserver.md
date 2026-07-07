# Citadel: Forged With Fire

This guide covers the `citadelserver` module in AlphaGSM.

`citadelserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux
baseline. The checked-in GitHub validation path for this server is
Docker-first through the shared `steamcmd-linux` runtime, with generic `tcp`
`query` / `info` on the managed main port rather than an A2S `queryport`
contract.

## Requirements

- Docker
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycitadels create citadelserver
```

Run setup:

```bash
alphagsm mycitadels setup
```

Start it:

```bash
alphagsm mycitadels start
```

Check it:

```bash
alphagsm mycitadels status
```

Stop it:

```bash
alphagsm mycitadels stop
```

## Setup Details

Setup configures:

- the game port (default `7777`)
- the Steam query port (default `27015`)
- the install directory
- SteamCMD downloads the native Linux dedicated-server payload for app `489650`
- AlphaGSM runs the validated Linux path through the shared `steamcmd-linux` Docker runtime

## Useful Commands

```bash
alphagsm mycitadels update
alphagsm mycitadels backup
```

## Notes

- Module name: `citadelserver`
- Default game port: `7777`
- Default query port: `27015`
- Supported Linux health contract: `query`, `info`, and `info --json` use generic `tcp` on the managed main game port

## Developer Notes

### Run File

- **Executable**: `CitadelServer.sh`
- **Fallback executable**: `Citadel/Binaries/Linux/CitadelServer-Linux-Shipping`
- **Location**: `<install_dir>/CitadelServer.sh`
- **Engine**: Native Linux dedicated server via SteamCMD
- **SteamCMD App ID**: `489650`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `50`
- **Template**: See [server-templates/citadelserver/](../server-templates/citadelserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
