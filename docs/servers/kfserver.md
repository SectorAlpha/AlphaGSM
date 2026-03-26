# Killing Floor

This guide covers the `kfserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mykfserver create kfserver
```

Run setup:

```bash
alphagsm mykfserver setup
```

Start it:

```bash
alphagsm mykfserver start
```

Check it:

```bash
alphagsm mykfserver status
```

Stop it:

```bash
alphagsm mykfserver stop
```

## Setup Details

Setup configures:

- the game port (default 7707)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mykfserver update
alphagsm mykfserver backup
```

## Notes

- Module name: `kfserver`
- Default port: 7707

## Developer Notes

### Run File

- **Executable**: `System/KillingFloorServer-bin`
- **Location**: `<install_dir>/System/KillingFloorServer-bin`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `215360`

### Server Configuration

- **Config file**: `system/KillingFloor.ini`
- **Template**: See [server-templates/kfserver/](../server-templates/kfserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
