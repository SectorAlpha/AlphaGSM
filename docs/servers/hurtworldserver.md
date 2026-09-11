# Hurtworld

This guide covers the `hurtworldserver` module in AlphaGSM.

`hurtworldserver` is currently `PASSED` on the documented Ubuntu 24.04 Linux baseline. The current GitHub integration lane still exercises both process and Docker runtime selection, and the validated Linux lifecycle stays aligned across both backends while local runs remain process-backed by default unless you opt into the Docker backend.

## Requirements

- `docker` for the validated branch-local `steamcmd-linux` runtime path
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhurtworl create hurtworldserver
```

Run setup:

```bash
alphagsm myhurtworl setup
```

Start it:

```bash
alphagsm myhurtworl start
```

Check it:

```bash
alphagsm myhurtworl status
```

Stop it:

```bash
alphagsm myhurtworl stop
```

## Setup Details

Setup configures:

- the game port (default 12871)
- the A2S query port (default 12872)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myhurtworl update
alphagsm myhurtworl backup
```

## Notes

- Module name: `hurtworldserver`
- Default port: `12871`
- Default query port: `12872`
- Validated Linux support path: native Linux dedicated payload on the shared `steamcmd-linux` runtime image

<!-- alphagsm-server-variables:start -->

## Server variables

After `create hurtworldserver`, inspect or change these with `set`:

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

- **Executable**: `Hurtworld.x86_64` (falls back to the shipped Linux executables when needed)
- **Location**: `<install_dir>/Hurtworld.x86_64`
- **Engine**: native Linux Unity dedicated server
- **SteamCMD App ID**: `405100`
- **Launch contract**: `-batchmode -nographics -exec "host <port>;queryport <queryport>;maxplayers <maxplayers>;servername <servername>" -logfile output.txt`

### Server Configuration

- **Config files**: runtime launch options plus `output.txt` for the validated headless log surface
- **Max players**: `50`
- **Template**: See [server-templates/hurtworldserver/](../server-templates/hurtworldserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
