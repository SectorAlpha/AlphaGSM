# GTA FiveM

This guide covers the `gtafivemserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mygtafivem create gtafivemserver
```

Run setup:

```bash
alphagsm mygtafivem setup
```

Start it:

```bash
alphagsm mygtafivem start
```

Check it:

```bash
alphagsm mygtafivem status
```

Stop it:

```bash
alphagsm mygtafivem stop
```

## Setup Details

Setup configures:

- the game port (default 30120)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mygtafivem update
alphagsm mygtafivem backup
```

## Notes

- Module name: `gtafivemserver`
- Default port: 30120

## Developer Notes

### Run File

- **Executable**: `opt/cfx-server/run.sh`
- **Location**: `<install_dir>/opt/cfx-server/run.sh`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/gtafivemserver/](../server-templates/gtafivemserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
