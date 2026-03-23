# Battle Cry of Freedom

This guide covers the `battlecryoffreedomserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybattlecr create battlecryoffreedomserver
```

Run setup:

```bash
alphagsm mybattlecr setup
```

Start it:

```bash
alphagsm mybattlecr start
```

Check it:

```bash
alphagsm mybattlecr status
```

Stop it:

```bash
alphagsm mybattlecr stop
```

## Setup Details

Setup configures:

- the game port (default 8263)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybattlecr update
alphagsm mybattlecr backup
```

## Notes

- Module name: `battlecryoffreedomserver`
- Default port: 8263

## Developer Notes

### Run File

- **Executable**: `BCoF.exe`
- **Location**: `<install_dir>/BCoF.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1362540`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/battlecryoffreedomserver/](../server-templates/battlecryoffreedomserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
