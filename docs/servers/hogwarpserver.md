# HogWarp

This guide covers the `hogwarpserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myhogwarps create hogwarpserver
```

Run setup:

```bash
alphagsm myhogwarps setup
```

Start it:

```bash
alphagsm myhogwarps start
```

Check it:

```bash
alphagsm myhogwarps status
```

Stop it:

```bash
alphagsm myhogwarps stop
```

## Setup Details

Setup configures:

- the game port (default 7777)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myhogwarps update
alphagsm myhogwarps backup
```

## Notes

- Module name: `hogwarpserver`
- Default port: 7777

## Developer Notes

### Run File

- **Executable**: `HogWarpServer.exe`
- **Location**: `<install_dir>/HogWarpServer.exe`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/hogwarpserver/](../server-templates/hogwarpserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
