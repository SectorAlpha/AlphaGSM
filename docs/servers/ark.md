# ARK: Survival Evolved

This guide covers the `ark` module in AlphaGSM.

`ark` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline.
The checked-in GitHub validation path for this server is Docker-first through
the shared `steamcmd-linux` runtime, with the real Linux dedicated server
answering A2S `query`, `info`, and `info --json` on the managed `queryport`.

## Requirements

- Docker or another supported AlphaGSM runtime backend
- SteamCMD access for app `376030`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myark create ark
```

Run setup:

```bash
alphagsm myark setup
```

Start it:

```bash
alphagsm myark start
```

Check it:

```bash
alphagsm myark status
```

Stop it:

```bash
alphagsm myark stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the query port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myark update
alphagsm myark backup
```

## Notes

- Module name: `ark`
- Default game port: `7777`
- Default query port: `27015`
- Validated Linux support path: Docker `steamcmd-linux` runtime with A2S `query` / `info` on `queryport`

## Developer Notes

### Run File

- **Executable**: `ShooterGame/Binaries/Linux/ShooterGameServer`
- **Location**: `<install_dir>/ShooterGame/Binaries/Linux/ShooterGameServer`
- **Engine**: Native Linux dedicated server via SteamCMD
- **SteamCMD App ID**: `376030`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `70`
- **Template**: See [server-templates/ark/](../server-templates/ark/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
