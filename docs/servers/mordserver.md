# Mordhau

This guide covers the `mordserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymordserv create mordserver
```

Run setup:

```bash
alphagsm mymordserv setup
```

Start it:

```bash
alphagsm mymordserv start
```

Check it:

```bash
alphagsm mymordserv status
```

Stop it:

```bash
alphagsm mymordserv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm mymordserv update
alphagsm mymordserv backup
```

## Notes

- Module name: `mordserver`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `MordhauServer.sh`
- **Location**: `<install_dir>/MordhauServer.sh`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `629800`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/mordserver/](../server-templates/mordserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
