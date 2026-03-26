# BattleBit Remastered

This guide covers the `battlebitserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybattlebi create battlebitserver
```

Run setup:

```bash
alphagsm mybattlebi setup
```

Start it:

```bash
alphagsm mybattlebi start
```

Check it:

```bash
alphagsm mybattlebi status
```

Stop it:

```bash
alphagsm mybattlebi stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybattlebi update
alphagsm mybattlebi backup
```

## Notes

- Module name: `battlebitserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `BattleBitDedicatedServer`
- **Location**: `<install_dir>/BattleBitDedicatedServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `689410`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `127`
- **Template**: See [server-templates/battlebitserver/](../server-templates/battlebitserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
