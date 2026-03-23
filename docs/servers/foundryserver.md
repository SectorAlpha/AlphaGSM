# FOUNDRY

This guide covers the `foundryserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myfoundrys create foundryserver
```

Run setup:

```bash
alphagsm myfoundrys setup
```

Start it:

```bash
alphagsm myfoundrys start
```

Check it:

```bash
alphagsm myfoundrys status
```

Stop it:

```bash
alphagsm myfoundrys stop
```

## Setup Details

Setup configures:

- the game port (default 37200)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myfoundrys update
alphagsm myfoundrys backup
```

## Notes

- Module name: `foundryserver`
- Default port: 37200

## Developer Notes

### Run File

- **Executable**: `FoundryDedicatedServer`
- **Location**: `<install_dir>/FoundryDedicatedServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2915550`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/foundryserver/](../server-templates/foundryserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
