# Nightingale

This guide covers the `nightingale` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mynighting create nightingale
```

Run setup:

```bash
alphagsm mynighting setup
```

Start it:

```bash
alphagsm mynighting start
```

Check it:

```bash
alphagsm mynighting status
```

Stop it:

```bash
alphagsm mynighting stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mynighting update
alphagsm mynighting backup
```

## Notes

- Module name: `nightingale`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `NWXServer.sh`
- **Location**: `<install_dir>/NWXServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3796810`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/nightingale/](../server-templates/nightingale/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
