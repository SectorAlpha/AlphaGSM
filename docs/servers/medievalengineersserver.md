# Medieval Engineers

This guide covers the `medievalengineersserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymedieval create medievalengineersserver
```

Run setup:

```bash
alphagsm mymedieval setup
```

Start it:

```bash
alphagsm mymedieval start
```

Check it:

```bash
alphagsm mymedieval status
```

Stop it:

```bash
alphagsm mymedieval stop
```

## Setup Details

Setup configures:

- the game port (default 27016)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymedieval update
alphagsm mymedieval backup
```

## Notes

- Module name: `medievalengineersserver`
- Default port: 27016

## Developer Notes

### Run File

- **Executable**: `DedicatedServer64/MedievalEngineersDedicated.exe`
- **Location**: `<install_dir>/DedicatedServer64/MedievalEngineersDedicated.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `367970`

### Server Configuration

- **Config files**: `global.cfg`
- **Template**: See [server-templates/medievalengineersserver/](../server-templates/medievalengineersserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
