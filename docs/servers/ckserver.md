# Core Keeper

This guide covers the `ckserver` module in AlphaGSM.

`ckserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myckserver create ckserver
```

Run setup:

```bash
alphagsm myckserver setup
```

Start it:

```bash
alphagsm myckserver start
```

Check it:

```bash
alphagsm myckserver status
```

Stop it:

```bash
alphagsm myckserver stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- the visible world name (`world`)
- the world slot index (`worldindex`, default `0`)
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myckserver update
alphagsm myckserver backup
```

## Notes

- Module name: `ckserver`
- Default port: 27015
- Linux startup uses the bundled `_launch.sh` wrapper, which starts `Xvfb` and launches the Unity server in `-batchmode`
- AlphaGSM uses the direct-connect game port for generic UDP `query` and `info` reachability checks
- Dedicated server state is written under `DedicatedServer/`
- The server writes connection details to `GameInfo.txt`

<!-- alphagsm-server-variables:start -->

## Server variables

After `create ckserver`, inspect or change these with `set`:

```bash
alphagsm myserver set --list
alphagsm myserver set KEY --describe
alphagsm myserver set KEY VALUE
```

This module does not declare schema-backed keys. `set --list` after
create is still the live source of truth.

<!-- alphagsm-server-variables:end -->

## Developer Notes

### Run File

- **Executable**: `_launch.sh`
- **Location**: `<install_dir>/_launch.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1963720`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `8`
- **Primary state directory**: `<install_dir>/DedicatedServer`
- **Runtime info files**: `GameInfo.txt`, `GameID.txt`, `CoreKeeperServerLog.txt`
- **Template**: See [server-templates/ckserver/](../server-templates/ckserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
