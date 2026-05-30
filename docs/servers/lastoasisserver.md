# Last Oasis

This guide covers the `lastoasisserver` module in AlphaGSM.

## Requirements

- SteamCMD access
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mylastoasi create lastoasisserver
```

Run setup:

```bash
alphagsm mylastoasi setup
```

Start it:

```bash
alphagsm mylastoasi start
```

Check it:

```bash
alphagsm mylastoasi status
```

Stop it:

```bash
alphagsm mylastoasi stop
```

## Setup Details

Setup configures:

- the game port (default 15000)
- the query port (default 15001)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mylastoasi update
alphagsm mylastoasi backup
```

## Notes

- Module name: `lastoasisserver`
- Default port: 15001

## Developer Notes

### Run File

- **Executable**: `Mist/Binaries/Linux/MistServer-Linux-Shipping`
- **Location**: `<install_dir>/Mist/Binaries/Linux/MistServer-Linux-Shipping`
- **Engine**: Native Linux dedicated server via SteamCMD
- **SteamCMD App ID**: `920720`

### Runtime Notes

- The validated Linux support path uses AlphaGSM's Docker-backed `steamcmd-linux` runtime.
- The current health surface is generic `tcp` on the managed main game port.
- `query`, `info`, and `info --json` do not use an A2S `queryport` contract on the working Linux path.

### Server Configuration

- **Config file**: See game module source
- **Max players**: `100`
- **Template**: See [server-templates/lastoasisserver/](../server-templates/lastoasisserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
