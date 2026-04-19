# Multi Theft Auto

This guide covers the `mtaserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymtaserve create mtaserver
```

Run setup:

```bash
alphagsm mymtaserve setup
```

Start it:

```bash
alphagsm mymtaserve start
```

Check it:

```bash
alphagsm mymtaserve status
```

Stop it:

```bash
alphagsm mymtaserve stop
```

## Setup Details

Setup configures:

- the game port (default 22003)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mymtaserve update
alphagsm mymtaserve backup
```

## Notes

- Module name: `mtaserver`
- Default port: 22003

## Developer Notes

### Run File

- **Executable**: `mta-server64`
- **Location**: `<install_dir>/mta-server64`
- **Engine**: Custom

### Server Configuration

- **Config file**: `mods/deathmatch/mtaserver.conf`
- **Template**: See [server-templates/mtaserver/](../server-templates/mtaserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
