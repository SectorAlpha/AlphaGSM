# Call of Duty: World at War

This guide covers the `codwawserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mycodwawse create codwawserver
```

Run setup:

```bash
alphagsm mycodwawse setup
```

Start it:

```bash
alphagsm mycodwawse start
```

Check it:

```bash
alphagsm mycodwawse status
```

Stop it:

```bash
alphagsm mycodwawse stop
```

## Setup Details

Setup configures:

- the game port (default 28960)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mycodwawse update
alphagsm mycodwawse backup
```

## Notes

- Module name: `codwawserver`
- Default port: 28960

## Developer Notes

### Run File

- **Executable**: `codwaw_lnxded`
- **Location**: `<install_dir>/codwaw_lnxded`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/codwawserver/](../server-templates/codwawserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
