# Motor Town: Behind The Wheel

This guide covers the `motortownserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymotortow create motortownserver
```

Run setup:

```bash
alphagsm mymotortow setup
```

Start it:

```bash
alphagsm mymotortow start
```

Check it:

```bash
alphagsm mymotortow status
```

Stop it:

```bash
alphagsm mymotortow stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymotortow update
alphagsm mymotortow backup
```

## Notes

- Module name: `motortownserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `MotorTown/Binaries/Win64/MotorTownServer-Win64-Shipping.exe`
- **Location**: `<install_dir>/MotorTown/Binaries/Win64/MotorTownServer-Win64-Shipping.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2223650`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/motortownserver/](../server-templates/motortownserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
