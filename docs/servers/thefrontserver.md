# The Front

This guide covers the `thefrontserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mythefront create thefrontserver
```

Run setup:

```bash
alphagsm mythefront setup
```

Start it:

```bash
alphagsm mythefront start
```

Check it:

```bash
alphagsm mythefront status
```

Stop it:

```bash
alphagsm mythefront stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mythefront update
alphagsm mythefront backup
```

## Notes

- Module name: `thefrontserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `ProjectWar/Binaries/Linux/TheFrontServer`
- **Location**: `<install_dir>/ProjectWar/Binaries/Linux/TheFrontServer`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `2334200`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `32`
- **Template**: See [server-templates/thefrontserver/](../server-templates/thefrontserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
