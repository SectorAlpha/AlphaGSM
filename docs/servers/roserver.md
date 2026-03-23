# Red Orchestra: Ostfront 41-45

This guide covers the `roserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myroserver create roserver
```

Run setup:

```bash
alphagsm myroserver setup
```

Start it:

```bash
alphagsm myroserver start
```

Check it:

```bash
alphagsm myroserver status
```

Stop it:

```bash
alphagsm myroserver stop
```

## Setup Details

Setup configures:

- the game port (default 7757)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myroserver update
alphagsm myroserver backup
```

## Notes

- Module name: `roserver`
- Default port: 7757

## Developer Notes

### Run File

- **Executable**: `System/ucc-bin`
- **Location**: `<install_dir>/System/ucc-bin`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `223250`

### Server Configuration

- **Config file**: `System/RedOrchestra.ini`
- **Template**: See [server-templates/roserver/](../server-templates/roserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
