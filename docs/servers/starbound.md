# Starbound

This guide covers the `starbound` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mystarboun create starbound
```

Run setup:

```bash
alphagsm mystarboun setup
```

Start it:

```bash
alphagsm mystarboun start
```

Check it:

```bash
alphagsm mystarboun status
```

Stop it:

```bash
alphagsm mystarboun stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mystarboun update
alphagsm mystarboun backup
```

## Notes

- Module name: `starbound`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `linux64/starbound_server`
- **Location**: `<install_dir>/linux64/starbound_server`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `211820`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/starbound/](../server-templates/starbound/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
