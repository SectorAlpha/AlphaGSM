# SCUM

This guide covers the `scumserver` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myscumserv create scumserver
```

Run setup:

```bash
alphagsm myscumserv setup
```

Start it:

```bash
alphagsm myscumserv start
```

Check it:

```bash
alphagsm myscumserv status
```

Stop it:

```bash
alphagsm myscumserv stop
```

## Setup Details

Setup configures:

- the game port (default 7779)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myscumserv update
alphagsm myscumserv backup
```

## Notes

- Module name: `scumserver`
- Default port: 7779

## Developer Notes

### Run File

- **Executable**: `SCUM/Binaries/Win64/SCUMServer.exe`
- **Location**: `<install_dir>/SCUM/Binaries/Win64/SCUMServer.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `3792580`

### Server Configuration

- **Config file**: See game module source
- **Max players**: `64`
- **Template**: See [server-templates/scumserver/](../server-templates/scumserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
