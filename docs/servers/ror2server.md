# Risk of Rain 2

This guide covers the `ror2server` module in AlphaGSM.

## Requirements

- `screen`
- SteamCMD runtime libraries (`lib32gcc-s1`, `lib32stdc++6`)
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myror2serv create ror2server
```

Run setup:

```bash
alphagsm myror2serv setup
```

Start it:

```bash
alphagsm myror2serv start
```

Check it:

```bash
alphagsm myror2serv status
```

Stop it:

```bash
alphagsm myror2serv stop
```

## Setup Details

Setup configures:

- the game port (default 27015)
- the install directory
- SteamCMD downloads the server files

## Useful Commands

```bash
alphagsm myror2serv update
alphagsm myror2serv backup
```

## Notes

- Module name: `ror2server`
- Default port: 27015

## Developer Notes

### Run File

- **Executable**: `Risk of Rain 2.exe`
- **Location**: `<install_dir>/Risk of Rain 2.exe`
- **Engine**: Custom (SteamCMD)
- **SteamCMD App ID**: `1180760`

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/ror2server/](../server-templates/ror2server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
