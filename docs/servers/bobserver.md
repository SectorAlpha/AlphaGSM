# Beasts of Bermuda

This guide covers the `bobserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mybobserve create bobserver
```

Run setup:

```bash
alphagsm mybobserve setup
```

Start it:

```bash
alphagsm mybobserve start
```

Check it:

```bash
alphagsm mybobserve status
```

Stop it:

```bash
alphagsm mybobserve stop
```

## Setup Details

Setup configures:

- the game port (default 7778)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mybobserve update
alphagsm mybobserve backup
```

## Notes

- Module name: `bobserver`
- Default port: 7778

## Developer Notes

### Run File

- **Executable**: `BeastsOfBermudaServer.sh`
- **Location**: `<install_dir>/BeastsOfBermudaServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `882430`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/bobserver/](../server-templates/bobserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
