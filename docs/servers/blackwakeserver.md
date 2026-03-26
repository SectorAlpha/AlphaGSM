# Blackwake

This guide covers the `blackwakeserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myblackwak create blackwakeserver
```

Run setup:

```bash
alphagsm myblackwak setup
```

Start it:

```bash
alphagsm myblackwak start
```

Check it:

```bash
alphagsm myblackwak status
```

Stop it:

```bash
alphagsm myblackwak stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myblackwak update
alphagsm myblackwak backup
```

## Notes

- Module name: `blackwakeserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Blackwake Dedicated Server.exe`
- **Location**: `<install_dir>/Blackwake Dedicated Server.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `423410`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `54`
- **Template**: See [server-templates/blackwakeserver/](../server-templates/blackwakeserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
