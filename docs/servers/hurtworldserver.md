# Hurtworld

This guide covers the `hurtworldserver` module in AlphaGSM.

## Requirements

- `screen`
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

- the game port (default 12872)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myhurtworl update
alphagsm myhurtworl backup
```

## Notes

- Module name: `hurtworldserver`
- Default port: 12872

## Developer Notes

### Run File

- **Executable**: `HurtworldDedicated`
- **Location**: `<install_dir>/HurtworldDedicated`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `405100`

### Server Configuration

- **Config files**: `hurtworld.cfg`
- **Max players**: `50`
- **Template**: See [server-templates/hurtworldserver/](../server-templates/hurtworldserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
