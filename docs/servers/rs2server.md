# Rising Storm 2: Vietnam

This guide covers the `rs2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myrs2serve create rs2server
```

Run setup:

```bash
alphagsm myrs2serve setup
```

Start it:

```bash
alphagsm myrs2serve start
```

Check it:

```bash
alphagsm myrs2serve status
```

Stop it:

```bash
alphagsm myrs2serve stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myrs2serve update
alphagsm myrs2serve backup
```

## Notes

- Module name: `rs2server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/VNGame.exe`
- **Location**: `<install_dir>/Binaries/Win64/VNGame.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `418480`

### Server Configuration

- **Config file**: `ROGame/Config/PCServer-ROGame.ini`
- **Template**: See [server-templates/rs2server/](../server-templates/rs2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
