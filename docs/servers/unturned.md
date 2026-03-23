# Unturned

This guide covers the `unturned` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myunturned create unturned
```

Run setup:

```bash
alphagsm myunturned setup
```

Start it:

```bash
alphagsm myunturned start
```

Check it:

```bash
alphagsm myunturned status
```

Stop it:

```bash
alphagsm myunturned stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myunturned update
alphagsm myunturned backup
```

## Notes

- Module name: `unturned`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `ServerHelper.sh`
- **Location**: `<install_dir>/ServerHelper.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1110390`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/unturned/](../server-templates/unturned/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
