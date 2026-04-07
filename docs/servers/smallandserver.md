# Smalland

This guide covers the `smallandserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mysmalland create smallandserver
```

Run setup:

```bash
alphagsm mysmalland setup
```

Start it:

```bash
alphagsm mysmalland start
```

Check it:

```bash
alphagsm mysmalland status
```

Stop it:

```bash
alphagsm mysmalland stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mysmalland update
alphagsm mysmalland backup
```

## Notes

- Module name: `smallandserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `SMALLANDServer.sh`
- **Location**: `<install_dir>/SMALLANDServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `808040`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/smallandserver/](../server-templates/smallandserver/) if available
- **Query/info behavior**: AlphaGSM uses a generic UDP reachability probe on the main game port because the dedicated server binds a silent UDP listener rather than exposing A2S details

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
