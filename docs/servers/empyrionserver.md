# Empyrion - Galactic Survival

This guide covers the `empyrionserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myempyrion create empyrionserver
```

Run setup:

```bash
alphagsm myempyrion setup
```

Start it:

```bash
alphagsm myempyrion start
```

Check it:

```bash
alphagsm myempyrion status
```

Stop it:

```bash
alphagsm myempyrion stop
```

## Setup Details

Setup configures:

- the game port (default 30004)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myempyrion update
alphagsm myempyrion backup
```

## Notes

- Module name: `empyrionserver`
- Default port: 30004

## Developer Notes

### Run File

- **Executable**: `EmpyrionDedicated.exe`
- **Location**: `<install_dir>/EmpyrionDedicated.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `530870`

### Server Configuration

- **Config files**: `dedicated.yaml`
- **Template**: See [server-templates/empyrionserver/](../server-templates/empyrionserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
