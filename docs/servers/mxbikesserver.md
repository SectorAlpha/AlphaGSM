# MX Bikes

This guide covers the `mxbikesserver` module in AlphaGSM.

## Requirements

- `screen`
- Python packages from `requirements.txt`

## Quick Start

Create the server:

```bash
alphagsm mymxbikess create mxbikesserver
```

Run setup:

```bash
alphagsm mymxbikess setup
```

Start it:

```bash
alphagsm mymxbikess start
```

Check it:

```bash
alphagsm mymxbikess status
```

Stop it:

```bash
alphagsm mymxbikess stop
```

## Setup Details

Setup configures:

- the game port (default 54210)
- the install directory
- downloads and extracts the server archive

## Useful Commands

```bash
alphagsm mymxbikess update
alphagsm mymxbikess backup
```

## Notes

- Module name: `mxbikesserver`
- Default port: 54210

## Developer Notes

### Run File

- **Executable**: `mxbikes_dedicated`
- **Location**: `<install_dir>/mxbikes_dedicated`
- **Engine**: Custom

### Server Configuration

- **Config file**: See game module source
- **Template**: See [server-templates/mxbikesserver/](../server-templates/mxbikesserver/) if available

### Maps and Mods

- **Map directory**: Check game documentation
- **Mod directory**: Check game documentation
- **Workshop support**: No
