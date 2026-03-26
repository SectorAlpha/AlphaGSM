# Unreal Tournament 99

This guide covers the `ut99server` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myut99serv create ut99server
```

Run setup:

```bash
alphagsm myut99serv setup
```

Start it:

```bash
alphagsm myut99serv start
```

Check it:

```bash
alphagsm myut99serv status
```

Stop it:

```bash
alphagsm myut99serv stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myut99serv update
alphagsm myut99serv backup
```

## Notes

- Module name: `ut99server`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `System/ucc-bin`
- **Location**: `<install_dir>/System/ucc-bin`
- **Engine**: Custom

### Server Configuration

- **Config file**: `System/UnrealTournament.ini`
- **Max players**: `16`
- **Template**: See [server-templates/ut99server/](../server-templates/ut99server/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
