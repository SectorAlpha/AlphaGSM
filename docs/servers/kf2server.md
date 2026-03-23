# Killing Floor 2

This guide covers the `kf2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mykf2serve create kf2server
```

Run setup:

```bash
alphagsm mykf2serve setup
```

Start it:

```bash
alphagsm mykf2serve start
```

Check it:

```bash
alphagsm mykf2serve status
```

Stop it:

```bash
alphagsm mykf2serve stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mykf2serve update
alphagsm mykf2serve backup
```

## Notes

- Module name: `kf2server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `Binaries/Win64/KFGameSteamServer.bin.x86_64`
- **Location**: `<install_dir>/Binaries/Win64/KFGameSteamServer.bin.x86_64`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `232130`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/kf2server/](../server-templates/kf2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
