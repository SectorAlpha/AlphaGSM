# The Forest

This guide covers the `theforestserver` module in AlphaGSM.

`theforestserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. Linux launches use Wine or Proton under Xvfb. AlphaGSM manages the native configuration and save paths for both process and Docker runtimes.

## Requirements

- `screen`
- Wine or Proton-GE on Linux
- `xvfb-run` on Linux process runtimes
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mythefores create theforestserver
```

Run setup:

```bash
alphagsm mythefores setup
```

Start it:

```bash
alphagsm mythefores start
```

Check it:

```bash
alphagsm mythefores status
```

Stop it:

```bash
alphagsm mythefores stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the Steam query port (default 27016)
- the Steam communication port (default 8766)
- the install directory
- SteamCMD downloads the server files
- the managed native configuration at `server-data/Server.cfg`
- the persistent save directory at `server-data/saves/`

You may set `queryport` and `steamport` after `create` and before `setup`.
AlphaGSM preserves those values and writes `Server.cfg` once the install
directory exists.

## Useful Commands

```bash
alphagsm mythefores update
alphagsm mythefores backup
```

## Notes

- Module name: `theforestserver`
- Default game port: 27015
- Default query port: 27016
- Default Steam communication port: 8766
- AlphaGSM `query`, `info`, and `info --json` use A2S on the managed query port.

## Developer Notes

### Run File

- **Executable**: `TheForestDedicatedServer.exe`
- **Location**: `<install_dir>/TheForestDedicatedServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `556450`

### Server Configuration

- **Config file**: `server-data/Server.cfg`
- **Save directory**: `server-data/saves/`
- **Template**: See [server-templates/theforestserver/](../server-templates/theforestserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
