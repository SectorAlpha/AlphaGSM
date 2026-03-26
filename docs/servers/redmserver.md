# RedM

This guide covers the `redmserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm myredmserv create redmserver
```

Run setup:

```bash
alphagsm myredmserv setup
```

Start it:

```bash
alphagsm myredmserv start
```

Check it:

```bash
alphagsm myredmserv status
```

Stop it:

```bash
alphagsm myredmserv stop
```

## Setup Details

Setup configures:

- the game port (default 30120)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm myredmserv update
alphagsm myredmserv backup
```

## Notes

- Module name: `redmserver`
- Default port: 30120

## Developer Notes

### Run File

- **Executable**: `run.sh`
- **Location**: `<install_dir>/run.sh`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/redmserver/](../server-templates/redmserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
