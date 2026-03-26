# Fear the Night

This guide covers the `fearthenightserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfearthen create fearthenightserver
```

Run setup:

```bash
alphagsm myfearthen setup
```

Start it:

```bash
alphagsm myfearthen start
```

Check it:

```bash
alphagsm myfearthen status
```

Stop it:

```bash
alphagsm myfearthen stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myfearthen update
alphagsm myfearthen backup
```

## Notes

- Module name: `fearthenightserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `Moonlight/Binaries/Win64/MoonlightServer.exe`
- **Location**: `<install_dir>/Moonlight/Binaries/Win64/MoonlightServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `764940`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/fearthenightserver/](../server-templates/fearthenightserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
