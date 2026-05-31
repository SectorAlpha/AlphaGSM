# Hurtworld

This guide covers the `hurtworldserver` module in AlphaGSM.

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
