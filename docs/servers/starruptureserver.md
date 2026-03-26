# StarRupture

This guide covers the `starruptureserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystarrupt create starruptureserver
```

Run setup:

```bash
alphagsm mystarrupt setup
```

Start it:

```bash
alphagsm mystarrupt start
```

Check it:

```bash
alphagsm mystarrupt status
```

Stop it:

```bash
alphagsm mystarrupt stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystarrupt update
alphagsm mystarrupt backup
```

## Notes

- Module name: `starruptureserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `StarRuptureServerEOS.exe`
- **Location**: `<install_dir>/StarRuptureServerEOS.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3809400`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/starruptureserver/](../server-templates/starruptureserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
